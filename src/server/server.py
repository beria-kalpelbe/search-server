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

MAX_PAYLOAD_SIZE = 1024

class SearchHandler(socketserver.BaseRequestHandler):
    
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
            
            print(f"Attempting SSL handshake from {self.client_address}")
            self.request = context.wrap_socket(self.request, server_side=True)
            print(f"SSL established with {self.client_address} using {self.request.version()}")
        
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
        self.search_algo.reread_on_query = self.config.reread_on_query
        if self.config.reread_on_query:
            print(f"REREAD_ON_QUERY enabled - file will be re-read on every search request")
        self.search_algo.prepare()
    
    def handle(self):
        try:
            while True:
                data = b""
                while True:
                    remaining = MAX_PAYLOAD_SIZE - len(data)
                    if remaining <= 0:
                        raise ValueError("Request exceeds maximum payload size of 1024 bytes")
                    
                    chunk = self.request.recv(min(remaining, 4096))
                    if not chunk:
                        break
                    
                    data += chunk
                    if b"\n" in data:
                        break
                if not data:
                    break
                data = data.rstrip(b"\x00")
                if len(data) == 0:
                    continue
                query = data.decode('utf-8').strip()
                print(f"Received query: {query}")
                results = list(self.search_algo.search(query))
                print(f"Search results: {results}")
                response = "STRING EXISTS\n" if results else "STRING NOT FOUND\n"
                self.request.sendall(response.encode('utf-8'))  
        except ValueError as e:
            print(f"Error handling connection from {self.client_address}: {e}")
            self.request.sendall(b"ERROR: Payload too large\n")
        except Exception as e:
            print(f"Error handling connection from {self.client_address}: {e}")
    
    def finish(self):
        if self.search_algo:
            self.search_algo.cleanup()

class ThreadedTCPServer(socketserver.ThreadingTCPServer):
    
    def __init__(self, server_address, RequestHandlerClass, config):
        self.config = config
        super().__init__(server_address, RequestHandlerClass)
    
    def finish_request(self, request, client_address):
        self.RequestHandlerClass(request, client_address, self, config=self.config)

def run_server(config_file: str = "src/config/server.conf"):
    config = Config(config_file)
    server = ThreadedTCPServer((config.host, config.port), SearchHandler, config)
    
    print(f"Starting server on {config.host}:{config.port}")
    print(f"SSL enabled: {config.use_ssl}")
    print(f"Search path: {config.linux_path}")
    print(f"Workers: {config.workers}")
    print(f"Search algorithm: {config.search_algorithm}")
    print(f"Maximum payload size: {MAX_PAYLOAD_SIZE} bytes")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    run_server() 