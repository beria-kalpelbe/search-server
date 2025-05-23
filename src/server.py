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
from src.search.algorithms.grep import GrepSearch
from src.config.config import Config
import datetime
from textwrap import dedent
import platform
import psutil
import functools
import cProfile

# Constants
MAX_PAYLOAD_SIZE = 1024
DEFAULT_THREAD_POOL_SIZE = 100
REQUEST_QUEUE_SIZE = 1000
RECV_BUFFER_SIZE = 8192


class SSLHandler:
    """
    High-speed SSL context manager for maximum performance
    """
    _ssl_context = None
    _context_initialized = False
    
    @classmethod
    def get_ssl_context(cls, ssl_cert, ssl_key):
        """
        Get or create an SSL context for maximum speed
        """
        start = time.time()
        if cls._context_initialized and cls._ssl_context:
            return cls._ssl_context
            
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        
        # Performance-first SSL configuration
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.maximum_version = ssl.TLSVersion.TLSv1_3
        
        # Load certificates
        context.load_cert_chain(ssl_cert, keyfile=ssl_key)
        
        # Ultra-fast cipher selection - prioritize speed over everything
        context.set_ciphers('ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE+AESGCM:!aNULL:!eNULL')
        
        # Maximum performance options
        context.options |= ssl.OP_NO_COMPRESSION      # Disable compression for speed
        context.options |= ssl.OP_SINGLE_DH_USE       # Use ephemeral DH keys
        context.options |= ssl.OP_SINGLE_ECDH_USE     # Use ephemeral ECDH keys
        context.options |= ssl.OP_NO_SSLv2            # Disable old protocols
        context.options |= ssl.OP_NO_SSLv3            # Disable old protocols
        
        # Enable session reuse for returning clients (huge performance boost)
        try:
            # These methods may not be available in all Python versions
            if hasattr(context, 'set_session_cache_mode'):
                context.set_session_cache_mode(ssl.SESS_CACHE_SERVER)
            if hasattr(context, 'set_session_timeout'):
                context.set_session_timeout(300)  # 5 minutes
            if hasattr(context, 'set_session_id_context'):
                context.set_session_id_context(b'search_srv')
        except (AttributeError, OSError):
            # Session caching not available or not supported
            pass
        
        # Store for reuse
        cls._ssl_context = context
        cls._context_initialized = True
        
        return context


class SearchHandler(socketserver.BaseRequestHandler):
    """
    Handles incoming client requests and processes search queries.

    Attributes:
        algorithm_instances (Dict[str, SearchAlgorithm]): Cached instances of search algorithms.
    """
    algorithm_instances: Dict[str, SearchAlgorithm] = {}
    
    # Precompiled responses for better performance
    RESPONSE_FOUND = b"STRING EXISTS\n"
    RESPONSE_NOT_FOUND = b"STRING NOT FOUND\n"
    RESPONSE_ERROR_ENCODING = b"ERROR: Invalid character encoding\n"
    RESPONSE_ERROR_PAYLOAD = b"ERROR: Payload too large\n"
    RESPONSE_ERROR_EMPTY = b"ERROR: Empty request\n"
    RESPONSE_ERROR_INTERNAL = b"ERROR: Internal server error\n"
    RESPONSE_ERROR_SSL_HANDSHAKE = b"ERROR: SSL handshake failed\n"

    def __init__(self, *args, **kwargs) -> None:
        self.config: Optional[Config] = kwargs.pop('config', None)
        self.search_algo: Optional[SearchAlgorithm] = None
        super().__init__(*args, **kwargs)

    def setup(self) -> None:
        """
        High-speed setup with SSL handling.
        """
        if self.config.use_ssl:
            self._setup_high_speed_ssl()
            
        # Initialize search algorithm (cached)
        self._initialize_search_algorithm()

    def _setup_high_speed_ssl(self) -> None:
        """
        SSL setup for maximum performance
        """
        try:
            # Get the SSL context
            context = SSLHandler.get_ssl_context(
                self.config.ssl_cert, 
                self.config.ssl_key
            )
            
            # Optimize the underlying socket before SSL wrapping
            try:
                # Enable TCP_NODELAY to reduce latency (critical for performance)
                self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                
                # Increase socket buffers for better throughput
                self.request.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 131072)  # 128KB
                self.request.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 131072)  # 128KB
                
                # Set keep-alive for better connection reuse
                self.request.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                
            except (OSError, AttributeError):
                # Some systems might not support all these options
                pass
            
            # Set handshake timeout to prevent hanging
            original_timeout = self.request.gettimeout()
            self.request.settimeout(3.0)  # 3 second timeout for handshake
            
            # Wrap socket with SSL - manual handshake for better control
            self.request = context.wrap_socket(
                self.request, 
                server_side=True,
                do_handshake_on_connect=True
            )
            
            # Perform handshake
            self.request.do_handshake()
            
            # Restore original timeout or set a reasonable one for data transfer
            self.request.settimeout(1.0)  # 10 seconds for data operations
            
        except ssl.SSLError as e:
            if self.config.debug:
                self.config.logger.error(f"\033[91mSSL handshake failed: {e}\033[0m")
            self.request.sendall(self.RESPONSE_ERROR_SSL_HANDSHAKE)
            raise
        except socket.timeout:
            if self.config.debug:
                self.config.logger.warning("\033[91mSSL handshake timeout\033[0m")
            raise
        except Exception as e:
            if self.config.debug:
                self.config.logger.error(f"\033[91mSSL setup error: {e}\033[0m")
            raise

    def _initialize_search_algorithm(self) -> None:
        """Initialize the search algorithm instance (or get from cache)"""
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
                'grep': GrepSearch,
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
        
        # Only log connections in debug mode or with lower frequency
        if self.config.debug:
            self.config.logger.info("\033[92m[%s] New connection established\033[0m", session_id)
            
        request_count = 0

        try:
            while True:
                try:
                    data = self._receive_request_optimized()
                    if data is None:
                        break
                except UnicodeDecodeError:
                    self.request.sendall(self.RESPONSE_ERROR_ENCODING)
                    return
                except ValueError:
                    self.request.sendall(self.RESPONSE_ERROR_PAYLOAD)
                    return
                    
                request_count += 1
                
                try:
                    # Ultra-fast query processing
                    query = self._extract_query_fast(data)
                    if not query:
                        self.request.sendall(self.RESPONSE_ERROR_EMPTY)
                        break
                    start = time.time()
                    # Process the query directly using cached algorithm
                    result = self.search_algo.search(query)
                    search_time = 1000 * (time.time() - start)
                    # Use pre-compiled response for maximum speed
                    if self.config.debug:
                        if result:
                            self.config.logger.info(
                                f"\033[92m✓ Found string: '{query}' in {search_time:.2f}ms\033[0m"
                            )
                        else:
                            self.config.logger.warning(
                                f"\033[93m⚠ String not found: '{query}' (searched in {search_time:.2f}ms)\033[0m"
                            )
                    self.request.sendall(self.RESPONSE_FOUND if result else self.RESPONSE_NOT_FOUND)
                    
                    # Minimal logging for performance
                    if self.config.debug:
                        self.config.logger.debug(
                            "[%s] Batch processed: %d requests",
                            session_id,
                            request_count
                        )
                
                except UnicodeDecodeError:
                    
                    self.request.sendall(self.RESPONSE_ERROR_ENCODING)
                except Exception as e:
                    if self.config.debug:
                        self.config.logger.error(
                            f"\033[91m[{session_id}] Error processing request #{request_count}: {str(e)}\033[0m"
                        )
                    self.request.sendall(self.RESPONSE_ERROR_INTERNAL)
                    
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            # Handle connection issues silently in non-debug mode
            if self.config.debug:
                self.config.logger.debug(
                    "[%s] Connection terminated after %d requests",
                    session_id,
                    request_count
                )
        except Exception as e:
            if self.config.debug:
                self.config.logger.error(
                    f"\033[91m[{session_id}] Unhandled error after {request_count} requests: {str(e)}\033[0m"
                )

    def _receive_request_optimized(self) -> Optional[bytes]:
        """
        Ultra-method to receive request payload.
        """
        # Try to get the complete request in one shot (most common case)
        try:
            data = self.request.recv(MAX_PAYLOAD_SIZE)
            if not data:
                return None
            
            # If we have a complete line, return it immediately
            if b"\n" in data:
                return data.split(b"\n")[0].rstrip(b"\x00\r")
            
            # If no newline and data is short, it might be incomplete
            if len(data) < MAX_PAYLOAD_SIZE:
                return data.rstrip(b"\x00\r")
                
            # For longer data without newline, it's likely an error
            raise ValueError("Payload too large or malformed")
            
        except socket.timeout:
            return None
        except ssl.SSLWantReadError:
            # SSL needs more data
            return None

    def _extract_query_fast(self, data: bytes) -> str:
        """
        Fast query extraction with minimal processing
        """
        # Remove null bytes and whitespace
        clean_data = data.rstrip(b"\x00\r\n ")
        
        if not clean_data:
            return ""
            
        # Convert to string
        query = clean_data.decode('utf-8')
        
        # Handle case sensitivity
        if not self.config.case_sensitive:
            query = query.lower()
            
        return query


class ThreadPoolMixIn:
    """
    Thread pool mixin for handling concurrent requests.
    """
    def __init__(self):
        self._thread_pool = ThreadPoolExecutor(
            max_workers=getattr(self, '_max_workers', DEFAULT_THREAD_POOL_SIZE),
            thread_name_prefix="Worker"
        )
        self._shutdown = False
        self._requests = queue.Queue(maxsize=REQUEST_QUEUE_SIZE)
        self._request_processors = []
        
        # Create multiple request processors for better parallel processing
        num_processors = min(8, max(1, getattr(self, '_max_workers', DEFAULT_THREAD_POOL_SIZE) // 8))
        for i in range(num_processors):
            processor = self._start_request_processor(i)
            self._request_processors.append(processor)
    
    def _start_request_processor(self, processor_id):
        """
        Starts a thread to process incoming requests from the queue.
        """
        def process_requests():
            while not self._shutdown:
                try:
                    request, client_address = self._requests.get(timeout=0.5)
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
            name=f"RequestProcessor-{processor_id}"
        )
        processor.start()
        return processor
    
    def process_request_thread(self, request, client_address):
        """
        Processes a request in a separate thread.
        """
        try:
            self.finish_request(request, client_address)
        finally:
            self.close_request(request)
    
    def process_request(self, request, client_address):
        """
        Processes a request by adding it to the request queue.
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
        """
        self._shutdown = True
        for _ in self._request_processors:
            try:
                self._requests.put((None, None), block=False)
            except:
                pass
                
        for processor in self._request_processors:
            try:
                processor.join(timeout=0.5)
            except:
                pass
                
        self._thread_pool.shutdown(wait=False)
        super().server_close()


class ThreadedTCPServer(ThreadPoolMixIn, socketserver.TCPServer):
    """
    A threaded TCP server that uses a thread pool to handle incoming requests.
    """
    daemon_threads = True
    allow_reuse_address = True  # Allow faster restart after shutdown
    request_queue_size = REQUEST_QUEUE_SIZE
    
    def __init__(self, server_address, RequestHandlerClass, config):
        """
        Initializes the server with the given address, request handler class,
        and configuration.
        """
        self.config = config
        self._max_workers = config.workers
        self._request_processors = []
        self._thread_pool = ThreadPoolExecutor(
            max_workers=self._max_workers,
            thread_name_prefix="Worker"
        )
        # Additional server-level optimizations
        socketserver.TCPServer.__init__(self, server_address, RequestHandlerClass)
        
        # Set server socket options for better performance
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, 'SO_REUSEPORT'):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except (OSError, AttributeError):
            pass
            
        ThreadPoolMixIn.__init__(self)
    
    def finish_request(self, request, client_address):
        """
        Finishes the request by creating a handler to process it.
        """
        self.RequestHandlerClass(request, client_address, self, config=self.config)
    
    def close_request(self, request):
        """
        Closes the request and releases resources.
        """
        try:
            request.close()
        except:
            pass


def run_server(config_file: str = "src/config/server.conf"):
    """
    Main function to run the high-speed search server.
    """
    config = Config(config_file)
    
    # Performance optimizations in configuration
    if config.workers <= 0:
        # Auto-configure optimal number of workers based on CPU cores
        config.workers = min(DEFAULT_THREAD_POOL_SIZE, psutil.cpu_count(logical=True) * 2)
    
    # Use server implementation
    server = ThreadedTCPServer((config.host, config.port), SearchHandler, config)
    VERSION = getattr(config, 'version', '1.0.0')
    start_time = datetime.datetime.now()
    
    ssl_status = "🔐 SSL ENABLED" if config.use_ssl else "🔓 SSL DISABLED"
    print(f"\033[92m🚀 High-Speed Search Server v{VERSION} - {ssl_status}\033[0m")
    print(f"\033[94m📡 Listening on {config.host}:{config.port}\033[0m")
    print(f"\033[93m📅 Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\033[0m")
    print(f"\033[96m⚡ Workers: {config.workers} | Algorithm: {config.search_algorithm}\033[0m")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\033[91m🛑 Shutting down server...\033[0m")
        server.shutdown()
        server.server_close()
        print(f"\033[92m✅ Server shutdown complete.\033[0m")


if __name__ == "__main__":
    import os
    if os.environ.get('PROFILE_SEARCH_SERVER'):
        import cProfile
        cProfile.run('run_server()', 'search_server.prof')
    else:
        run_server()