"""Multi-threaded search server with SSL support."""

import socket
import ssl
import socketserver
import threading
import time
from typing import Type, Optional
from src.search.base import SearchAlgorithm
from src.search.algorithms import (
    SimpleSearch,
    InMemorySearch,
    BinarySearch,
    HashSearch,
    RegexSearch,
    BloomFilterSearch
)
from src.config.config import Config

class SearchHandler(socketserver.BaseRequestHandler):
    """Handler for search requests."""
    
    def __init__(self, *args, **kwargs):
        self.config = kwargs.pop('config', None)
        self.search_algo: Optional[SearchAlgorithm] = None
        super().__init__(*args, **kwargs)
    
    def setup(self):
        """Set up the connection and initialize search algorithm."""
        if self.config.use_ssl:
            try:
                # Create SSL context with secure defaults
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.minimum_version = ssl.TLSVersion.TLSv1_2  # Set minimum TLS version
                
                # Load certificate and key
                context.load_cert_chain(self.config.ssl_cert, keyfile=self.config.ssl_key)
                
                # Set modern cipher suites (remove deprecated options)
                context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20')
                
                # Print debug info to help troubleshoot
                print(f"Attempting SSL handshake from {self.client_address}")
                self.request = context.wrap_socket(self.request, server_side=True)
                print(f"SSL established with {self.client_address} using {self.request.version()}")
            except ssl.SSLError as e:
                print(f"SSL Error with {self.client_address}: {e}")
                # Don't attempt to shutdown - this can cause additional errors
                self.request.close()
                raise
            except Exception as e:
                print(f"Error setting up SSL with {self.client_address}: {e}")
                self.request.close()
                raise
        
        # Initialize search algorithm based on configuration
        algorithm_map = {
            'simple': SimpleSearch,
            'inmemory': InMemorySearch,
            'binary': BinarySearch,
            'hash': HashSearch,
            'regex': RegexSearch,
            'bloom': BloomFilterSearch
        }
        
        algorithm_class = algorithm_map.get(self.config.search_algorithm.lower(), InMemorySearch)
        self.search_algo = algorithm_class(self.config.linux_path)
        if self.config.reread_on_query:
            self.search_algo.reread_on_query = True
        self.search_algo.prepare()
    
    def handle(self):
        """Handle incoming search requests."""
        try:
            while True:
                # Receive data with buffer overflow protection
                data = b""
                while True:
                    chunk = self.request.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if len(data) > 1024 * 1024:  # 1MB limit
                        raise ValueError("Request too large")
                    if b"\n" in data:
                        break
                
                if not data:
                    break
                
                # Get the search query (remove newline)
                query = data.decode('utf-8').strip()
                
                # Perform search
                results = list(self.search_algo.search(query))
                
                # Send simple response
                response = "STRING EXISTS\n" if results else "STRING NOT FOUND\n"
                self.request.sendall(response.encode('utf-8'))
                
        except Exception as e:
            print(f"Error handling connection from {self.client_address}: {e}")
    
    def finish(self):
        """Clean up resources."""
        if self.search_algo:
            self.search_algo.cleanup()

class ThreadedTCPServer(socketserver.ThreadingTCPServer):
    """Threaded TCP server with SSL support."""
    
    def __init__(self, server_address, RequestHandlerClass, config):
        self.config = config
        super().__init__(server_address, RequestHandlerClass)
    
    def finish_request(self, request, client_address):
        """Finish one request by instantiating RequestHandlerClass."""
        self.RequestHandlerClass(request, client_address, self, config=self.config)

def run_server(config_file: str = "server.conf"):
    """Run the search server.
    
    Args:
        config_file: Path to configuration file
    """
    # Load configuration
    config = Config(config_file)
    
    # Create server
    server = ThreadedTCPServer((config.host, config.port), SearchHandler, config)
    
    # Start server
    print(f"Starting server on {config.host}:{config.port}")
    print(f"SSL enabled: {config.use_ssl}")
    print(f"Search path: {config.linux_path}")
    print(f"Workers: {config.workers}")
    print(f"Search algorithm: {config.search_algorithm}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    run_server() 