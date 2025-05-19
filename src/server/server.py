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
from textwrap import dedent
import platform
import psutil

# Constants
MAX_PAYLOAD_SIZE = 1024
DEFAULT_THREAD_POOL_SIZE = 100
REQUEST_QUEUE_SIZE = 1000
RECV_BUFFER_SIZE = 8192


class SearchHandler(socketserver.BaseRequestHandler):
    """
    Handles incoming client requests and processes search queries.

    Attributes:
        algorithm_instances (Dict[str, SearchAlgorithm]): Cached instances of search algorithms.
    """
    algorithm_instances: Dict[str, SearchAlgorithm] = {}

    def __init__(self, *args, **kwargs) -> None:
        self.config: Optional[Config] = kwargs.pop('config', None)
        self.search_algo: Optional[SearchAlgorithm] = None
        super().__init__(*args, **kwargs)

    def setup(self) -> None:
        """
        Sets up the handler, including SSL wrapping and algorithm initialization.
        """
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
            algorithm_class = algorithm_map.get(
                self.config.search_algorithm.lower(), InMemorySearch
            )
            self.algorithm_instances[algo_key] = algorithm_class(
                self.config.linux_path, self.config.reread_on_query
            )
        self.search_algo = self.algorithm_instances[algo_key]
        self.search_algo.reread_on_query = self.config.reread_on_query

    def handle(self) -> None:
        """
        Handles client connections and processes search requests.
        """
        client_ip, client_port = self.client_address
        session_id = f"{client_ip}:{client_port}"
        self.config.logger.info("[%s] New connection established", session_id)
        request_count = 0

        try:
            while True:
                try:
                    data = self._receive_request(session_id)
                    if data is None:
                        break
                except UnicodeDecodeError:
                    self._handle_invalid_encoding(session_id)
                    return
                except ValueError as e:
                    self._handle_payload_too_large(session_id, str(e))
                    return

                request_count += 1
                try:
                    query = data.decode('utf-8').strip()
                except UnicodeDecodeError:
                    self._handle_invalid_encoding(session_id)
                    return

                if not query:
                    self._handle_empty_request(session_id, request_count)
                    continue

                self._process_valid_query(session_id, request_count, query)

        except (ConnectionResetError, ConnectionAbortedError) as e:
            self.config.logger.warning(
                "[%s] Connection terminated after %d requests: %s",
                session_id,
                request_count,
                str(e)
            )
        except Exception as e:
            self._handle_unexpected_error(session_id, request_count, e)

    def _receive_request(self, session_id: str) -> Optional[bytes]:
        """
        Receives and validates a complete request payload.

        Args:
            session_id (str): Client identifier for logging.

        Returns:
            Optional[bytes]: Received payload or None if connection closed.

        Raises:
            ValueError: If payload exceeds MAX_PAYLOAD_SIZE.
            UnicodeDecodeError: If invalid UTF-8 sequence detected.
        """
        data = bytearray()
        while True:
            remaining = MAX_PAYLOAD_SIZE - len(data)
            if remaining <= 0:
                raise ValueError(f"Payload exceeds {MAX_PAYLOAD_SIZE} bytes")

            chunk = self.request.recv(min(remaining, 4096))
            if not chunk:
                return None

            try:
                if b"\n" in chunk:
                    test_chunk = chunk.split(b"\n")[0]
                    test_chunk.decode('utf-8')
            except UnicodeDecodeError:
                raise

            data.extend(chunk)
            if b"\n" in chunk:
                break

        return data.rstrip(b"\x00")

    def _handle_invalid_encoding(self, session_id: str) -> None:
        """
        Handles invalid character encoding errors.
        """
        self.config.logger.error("[%s] Invalid character encoding detected", session_id)
        try:
            self.request.sendall(b"ERROR: Invalid character encoding\n")
        except OSError:
            self.config.logger.warning("[%s] Failed to send encoding error response", session_id)

    def _handle_payload_too_large(self, session_id: str, error_msg: str) -> None:
        """
        Handles oversized payload errors.
        """
        log_msg = (
            f"[{session_id}] Request exceeds maximum payload size of {MAX_PAYLOAD_SIZE} bytes"
            if self.config.debug else f"[{session_id}] Payload size exceeded"
        )
        self.config.logger.error(log_msg)
        try:
            self.request.sendall(b"ERROR: Payload too large\n")
        except OSError:
            self.config.logger.warning("[%s] Failed to send size error response", session_id)

    def _handle_empty_request(self, session_id: str, request_count: int) -> None:
        """
        Handles empty query requests.
        """
        self.config.logger.warning(
            "[%s] Request #%d: Empty request received",
            session_id,
            request_count
        )
        try:
            self.request.sendall(b"ERROR: Empty request\n")
        except OSError:
            self.config.logger.warning(
                "[%s] Failed to send empty request response",
                session_id
            )

    def _process_valid_query(self, session_id: str, request_count: int, query: str) -> None:
        """
        Processes a valid search query.

        Args:
            session_id (str): Client identifier for logging.
            request_count (int): The number of requests processed for this session.
            query (str): The search query.
        """
        log_query = f"{query[:30]}..." if len(query) > 30 else query
        self.config.logger.info(
            "[%s] Request #%d: Search query '%s'",
            session_id,
            request_count,
            log_query
        )

        if not self.config.case_sensitive:
            query = query.lower()

        search_start = time.time()
        result = self.search_algo.search(query)
        search_time = time.time() - search_start

        status = "FOUND" if result else "NOT FOUND"
        self.config.logger.info(
            "[%s] Response #%d: %s (%.2fms)",
            session_id,
            request_count,
            status,
            search_time * 1000,
        )

        response = "STRING EXISTS\n" if result else "STRING NOT FOUND\n"
        try:
            self.request.sendall(response.encode('utf-8'))
        except OSError as e:
            self.config.logger.warning(
                "[%s] Failed to send response #%d: %s",
                session_id,
                request_count,
                str(e)
            )

    def _handle_unexpected_error(self, session_id: str, request_count: int, error: Exception) -> None:
        """
        Handles unexpected server errors.

        Args:
            session_id (str): Client identifier for logging.
            request_count (int): The number of requests processed for this session.
            error (Exception): The exception that occurred.
        """
        error_msg = str(error) if self.config.debug else "Internal server error"
        self.config.logger.error(
            "[%s] Unhandled exception on request #%d: %s",
            session_id,
            request_count,
            error_msg,
            exc_info=self.config.debug
        )
        try:
            self.request.sendall(b"ERROR: Internal server error\n")
        except OSError:
            self.config.logger.warning("[%s] Failed to send error response", session_id)

class ThreadPoolMixIn:
    """
    Mixin class to handle threading for incoming requests.
    It provides a thread pool for processing incoming requests
    and manages the lifecycle of threads and the request queue. It ensures
    that requests are handled efficiently and prevents the server from being
    overwhelmed by too many simultaneous connections.
    """
    def __init__(self):
        self._thread_pool = ThreadPoolExecutor(
            max_workers=getattr(self, '_max_workers', DEFAULT_THREAD_POOL_SIZE),
            thread_name_prefix="SearchWorker"
        )
        self._shutdown = False
        self._requests = queue.Queue(maxsize=REQUEST_QUEUE_SIZE)
        self._request_processor = self._start_request_processor()
    
    def _start_request_processor(self):
        """
        Starts a thread to process incoming requests from the queue.
        This thread continuously checks the queue for new requests and
        processes them using the thread pool.
        """
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
        """
        Processes a request in a separate thread.
        This method is called by the thread pool to handle the request.
        It ensures that the request is properly finished and closed.
        
        Args:
            request: The request object to process.
            client_address: The address of the client making the request.
        """
        
        try:
            self.finish_request(request, client_address)
        finally:
            self.close_request(request)
    
    def process_request(self, request, client_address):
        """
        Processes a request by adding it to the request queue.
        This method is called by the server when a new request is received.
        
        Args:
            request: The request object to process.
            client_address: The address of the client making the request.
        """
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
        """
        Closes the server and shuts down the thread pool.
        This method is called when the server is shutting down.
        It ensures that all threads are properly terminated and resources
        are released.
        """
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
    """
    A threaded TCP server that uses a thread pool to handle incoming requests.
    It inherits from both ThreadPoolMixIn and socketserver.TCPServer.
    This class is responsible for managing the server's lifecycle, including
    starting and stopping the server, as well as handling incoming connections.
    """
    daemon_threads = True
    allow_reuse_address = False
    allow_reuse_port = False
    request_queue_size = REQUEST_QUEUE_SIZE
    
    def __init__(self, server_address, RequestHandlerClass, config):
        """
        Initializes the server with the given address, request handler class,
        and configuration.
        Args:
            server_address: The address to bind the server to.
            RequestHandlerClass: The class that handles incoming requests.
            config: The configuration object containing server settings.
        """
        self.config = config
        self._max_workers = config.workers
        self._threads = []
        self._thread_pool = ThreadPoolExecutor(max_workers=self._max_workers)
        socketserver.TCPServer.__init__(self, server_address, RequestHandlerClass)
        ThreadPoolMixIn.__init__(self)
    
    def finish_request(self, request, client_address):
        """
        Finishes the request by creating a new thread to handle it.
        This method is called by the server when a new request is received.
        Args:
            request: The request object to process.
            client_address: The address of the client making the request.
        """
        self.RequestHandlerClass(request, client_address, self, config=self.config)
    
    def close_request(self, request):
        """
        Closes the request and releases any resources associated with it.
        This method is called when the request has been processed and is no
        longer needed.
        Args:
            request: The request object to close.
        """
        try:
            request.close()
        except:
            pass

def run_server(config_file: str = "src/config/server.conf"):
    """
    Main function to run the search server.
    It initializes the server with the given configuration file,
    sets up logging, and starts the server.
    Args:
        config_file (str): Path to the configuration file.
    """
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
    
    config.logger.info("Server configuration details:")  if config.debug else None
    config.logger.info(f"  - Search Path: {config.linux_path}")  if config.debug else None
    config.logger.info(f"  - Request Queue Size: {REQUEST_QUEUE_SIZE}")  if config.debug else None
    
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