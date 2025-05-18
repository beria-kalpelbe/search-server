import socket
import ssl
import socketserver
import threading
import time
import queue
from concurrent.futures import ThreadPoolExecutor
from typing import Type, Optional, Dict
from src.search.base import SearchAlgorithm
from src.search.algorithms.simple import SimpleSearch
from src.search.algorithms.inmemory import InMemorySearch
from src.search.algorithms.binary import BinarySearch
from src.search.algorithms.hash import HashSearch
from src.search.algorithms.regex import RegexSearch
from src.search.algorithms.bloomfilter import BloomFilterSearch
from src.search.algorithms.boyermoore import BoyerMoore
from src.search.algorithms.rabinkarp import RabinKarp
from src.search.algorithms.kmp import KMP
from src.config.config import Config
import datetime
import socket
from textwrap import dedent
import platform
import psutil

MAX_PAYLOAD_SIZE = 1024
DEFAULT_THREAD_POOL_SIZE = 100
REQUEST_QUEUE_SIZE = 1000
RECV_BUFFER_SIZE = 8192

class SearchHandler(socketserver.BaseRequestHandler):
    algorithm_instances: Dict[str, SearchAlgorithm] = {}
    
    def __init__(self, *args, **kwargs):
        self.config = kwargs.pop('config', None)
        self.search_algo: Optional[SearchAlgorithm] = None
        super().__init__(*args, **kwargs)
    
    def setup(self):
        if self.config.use_ssl:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.maximum_version = ssl.TLSVersion.TLSv1_3
            context.load_cert_chain(self.config.ssl_cert, keyfile=self.config.ssl_key)
            context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20')
            self.request = context.wrap_socket(self.request, server_side=True)
        algo_key = f"{self.config.search_algorithm}_{self.config.linux_path}"
        if algo_key not in self.algorithm_instances:
            algorithm_map = {
                'simple': SimpleSearch,
                'inmemory': InMemorySearch,
                'binary': BinarySearch,
                'hash': HashSearch,
                'regex': RegexSearch,
                'bloom': BloomFilterSearch,
                'boyermoore': BoyerMoore,
                'rabinkarp': RabinKarp,
                'kmp': KMP,
            }
            algorithm_class = algorithm_map.get(self.config.search_algorithm.lower(), InMemorySearch)
            self.algorithm_instances[algo_key] = algorithm_class(self.config.linux_path, self.config.reread_on_query)
            # self.algorithm_instances[algo_key].prepare()
        self.search_algo = self.algorithm_instances[algo_key]
        self.search_algo.reread_on_query = self.config.reread_on_query

    def handle(self):
        request_start = time.time()
        client_ip, client_port = self.client_address
        session_id = f"{client_ip}:{client_port}"
        self.config.logger.info(f"[{session_id}] New connection established")
        request_count = 0
        try:
            while True:
                data = bytearray()
                while True:
                    remaining = MAX_PAYLOAD_SIZE - len(data)
                    if remaining <= 0:
                        self.config.logger.error(f"[{session_id}] Request exceeds maximum payload size of {MAX_PAYLOAD_SIZE} bytes")
                        self.request.sendall(b"ERROR: Payload too large\n")
                        return None
                    chunk = self.request.recv(min(remaining, 4096))
                    if not chunk:
                        break
                    data.extend(chunk)
                    if b"\n" in chunk:
                        break
                if not data:
                    self.config.logger.info(f"[{session_id}] Connection closed after {request_count} requests" if request_count > 0 else f"[{session_id}] Connection closed without any requests")
                    break
                request_count += 1
                query = data.rstrip(b"\x00").decode('utf-8').strip()
                if not query:
                    self.config.logger.warning(f"[{session_id}] Request #{request_count}: Empty request received")
                    self.request.sendall(b"ERROR: Empty request\n")
                    continue
                log_query = f"{query[:30]}..." if len(query) > 30 else query
                self.config.logger.info(f"[{session_id}] Request #{request_count}: Search query '{log_query}' ({len(data)} bytes)")
                if self.config.debug:
                    self.config.logger.debug(f"[{session_id}] Full query: '{query}'")
                if not self.config.case_sensitive:
                    query = query.lower()
                # self.config.logger.info(f"Time before search elapsed: {(1000*(time.time() - request_start)):.2f} ms")
                search_start = time.time()
                result = self.search_algo.search(query)
                search_time = time.time() - search_start
                status = "FOUND" if result else "NOT FOUND"
                self.config.logger.info(f"[{session_id}] Response #{request_count}: {status} (took {(search_time*1000):.2f}ms)")
                response = "STRING EXISTS\n" if result else "STRING NOT FOUND\n"
                self.request.sendall(response.encode('utf-8'))
        except ConnectionResetError:
            self.config.logger.warning(f"[{session_id}] Connection reset by peer after {request_count} requests")
        except ConnectionAbortedError:
            self.config.logger.warning(f"[{session_id}] Connection aborted after {request_count} requests")
        except ValueError as e:
            self.config.logger.error(f"[{session_id}] Value error on request #{request_count}: {str(e)}")
            try:
                self.request.sendall(b"ERROR: Payload too large\n")
                self.config.logger.info(f"[{session_id}] Sent error response to client")
            except:
                self.config.logger.warning(f"[{session_id}] Failed to send error response - connection may be closed")
        except UnicodeDecodeError as e:
            self.config.logger.error(f"[{session_id}] Invalid encoding in request #{request_count}: {str(e)}")
            try:
                self.request.sendall(b"ERROR: Invalid character encoding\n")
            except:
                pass
        except Exception as e:
            self.config.logger.error(f"[{session_id}] Unhandled exception on request #{request_count}: {e}", exc_info=True)
            try:
                self.request.sendall(b"ERROR: Internal server error\n")
            except:
                pass

class ThreadPoolMixIn:
    def __init__(self):
        self._thread_pool = ThreadPoolExecutor(
            max_workers=getattr(self, '_max_workers', DEFAULT_THREAD_POOL_SIZE),
            thread_name_prefix="SearchWorker"
        )
        self._shutdown = False
        self._requests = queue.Queue(maxsize=REQUEST_QUEUE_SIZE)
        self._request_processor = self._start_request_processor()
    
    def _start_request_processor(self):
        def process_requests():
            while not self._shutdown:
                try:
                    request, client_address = self._requests.get(timeout=1)
                    if request is None:
                        break
                    self._thread_pool.submit(self.process_request_thread, request, client_address)
                except queue.Empty:
                    continue
                except Exception:
                    if not self._shutdown:
                        continue
        processor = threading.Thread(
            target=process_requests,
            daemon=True,
            name="RequestProcessor"
        )
        processor.start()
        return processor
    
    def process_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        finally:
            self.close_request(request)
    
    def process_request(self, request, client_address):
        if self._shutdown:
            return
        try:
            self._requests.put((request, client_address), block=False)
        except queue.Full:
            try:
                request.sendall(b"ERROR: Server too busy\n")
            finally:
                self.close_request(request)
    
    def server_close(self):
        self._shutdown = True
        try:
            self._requests.put((None, None), block=False)
            self._request_processor.join(timeout=1)
        except:
            pass
        finally:
            self._thread_pool.shutdown(wait=False)
            super().server_close()

class ThreadedTCPServer(ThreadPoolMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = REQUEST_QUEUE_SIZE
    
    def __init__(self, server_address, RequestHandlerClass, config):
        self.config = config
        self._max_workers = config.workers
        socketserver.TCPServer.__init__(self, server_address, RequestHandlerClass)
        ThreadPoolMixIn.__init__(self)
    
    def finish_request(self, request, client_address):
        self.RequestHandlerClass(request, client_address, self, config=self.config)
    
    def close_request(self, request):
        try:
            request.close()
        except:
            pass

def run_server(config_file: str = "src/config/server.conf"):
    config = Config(config_file)
    
    if config.workers <= 0:
        config.workers = DEFAULT_THREAD_POOL_SIZE
    
    server = ThreadedTCPServer((config.host, config.port), SearchHandler, config)

    VERSION = getattr(config, 'version', '1.0.0')
    BUILD_DATE = getattr(config, 'build_date', 'Unknown')
    
    hostname = socket.gethostname()
    start_time = datetime.datetime.now()
    start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    
    banner = f"""
    ┌────────────────────────────────────────────────────────────┐
    │                     SEARCH SERVER v1.0.0                   │
    ├────────────────────────────────────────────────────────────┤
     Host: {config.host:<15}     Port: {config.port:<6}  
     SSL: {('✓' if config.use_ssl else '✗'):<3}\t\t  Started: {start_time_str} 
     Algorithm: {config.search_algorithm:<12}   Workers: {config.workers:<3}                    
    └────────────────────────────────────────────────────────────┘
    ┌────────────────────────────────────────────────────────────┐
    """
    
    for line in dedent(banner).strip().split('\n'):
        config.logger.info(line)
    
    config.logger.info("Server configuration details:")
    config.logger.info(f"  - Search Path: {config.linux_path}")
    config.logger.info(f"  - Request Queue Size: {REQUEST_QUEUE_SIZE}")
    
    try:        
        config.logger.info("System information:") if config.debug else None
        config.logger.info(f"  - OS: {platform.system()} {platform.release()}") if config.debug else None
        config.logger.info(f"  - CPU: {psutil.cpu_count(logical=True)} cores") if config.debug else None
        mem = psutil.virtual_memory()
        config.logger.info(f"  - Memory: {mem.total // (1024**3)}GB total, {mem.available // (1024**3)}GB available") if config.debug else None
        
        disk = psutil.disk_usage(config.linux_path)
        config.logger.info(f"  - Disk: {disk.total // (1024**3)}GB total, {disk.free // (1024**3)}GB free on search path") if config.debug else None
    except ImportError:
        config.logger.debug("psutil not available, skipping system information") if config.debug else None
    
    config.logger.warning(f"[{start_time_str}] Search server started successfully on {config.host}:{config.port}")
    config.logger.warning("Waiting for incoming connections...")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        shutdown_time = datetime.datetime.now()
        uptime = shutdown_time - start_time
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"
        
        shutdown_banner = f"""
        ┌────────────────────────────────────────────────────────────┐
        │               INITIATING SERVER SHUTDOWN                   │
        ├────────────────────────────────────────────────────────────┤
          Time: {shutdown_time.strftime("%Y-%m-%d %H:%M:%S")}
          Server uptime: {uptime_str:<43} 
        └────────────────────────────────────────────────────────────┘
        """
        
        for line in dedent(shutdown_banner).strip().split('\n'):
            config.logger.warning(line)
            
        server.shutdown()
        server.server_close()
        config.logger.warning("Server shutdown complete.")

if __name__ == "__main__":
    run_server()