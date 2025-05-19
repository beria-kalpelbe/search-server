import socket
import ssl
import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List


class SearchClient:
    """
    A client for connecting to a search server and sending queries.

    Attributes:
        host (str): The server hostname.
        port (int): The server port.
        use_ssl (bool): Whether to use SSL for the connection.
        cert_path (str): Path to the server certificate for SSL verification.
    """

    def __init__(self, host: str, port: int, use_ssl: bool = True, cert_path: str = None) -> None:
        """
        Initializes the SearchClient.

        Args:
            host (str): The server hostname.
            port (int): The server port.
            use_ssl (bool): Whether to use SSL for the connection.
            cert_path (str): Path to the server certificate for SSL verification.
        """
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.cert_path = cert_path

    def create_connection(self) -> socket.socket:
        """
        Creates a socket connection to the server.

        Returns:
            socket.socket: The connected socket object.

        Raises:
            Exception: If the connection fails.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if self.use_ssl:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.maximum_version = ssl.TLSVersion.TLSv1_3

            if self.cert_path:
                context.load_verify_locations(self.cert_path)
            else:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

            sock = context.wrap_socket(sock, server_hostname=self.host)

        sock.connect((self.host, self.port))
        return sock

    def search(self, query: str) -> str:
        """
        Sends a search query to the server and retrieves the response.

        Args:
            query (str): The search query.

        Returns:
            str: The server's response.

        Raises:
            ValueError: If an error occurs during communication.
        """
        try:
            with self.create_connection() as sock:
                sock.sendall(f"{query}\n".encode('utf-8'))
                response = sock.recv(1024).decode('utf-8').strip()
                print(f"Response: {response}")
                return response
        except socket.error as e:
            raise ValueError(f"Socket error occurred during search: {e}")
        except Exception as e:
            raise ValueError(f"Error during search: {e}")


def run_concurrent_searches(client: SearchClient, queries: List[str], num_threads: int = 10) -> None:
    """
    Runs multiple search queries concurrently.

    Args:
        client (SearchClient): The search client instance.
        queries (List[str]): A list of search queries.
        num_threads (int): The number of concurrent threads.
    """
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_query = {
            executor.submit(client.search, query): query
            for query in queries
        }

        for future in as_completed(future_to_query):
            query = future_to_query[future]
            try:
                found = future.result()
                print(f"Query '{query}': {found}")
            except Exception as e:
                print(f"Query '{query}' generated an exception: {e}")


def main() -> None:
    """
    The main entry point for the search client application.
    Parses command-line arguments and runs the client.
    """
    parser = argparse.ArgumentParser(description='Search client for the algorithm server')
    parser.add_argument('--host', default='localhost', help='Server hostname')
    parser.add_argument('--port', type=int, default=8443, help='Server port')
    parser.add_argument('--no-ssl', action='store_true', help='Disable SSL')
    parser.add_argument('--cert', help='Path to server certificate for verification')
    parser.add_argument('--queries', nargs='+', default=['test'], help='Search queries to send')
    parser.add_argument('--threads', type=int, default=10, help='Number of concurrent threads')

    args = parser.parse_args()

    client = SearchClient(
        host=args.host,
        port=args.port,
        use_ssl=not args.no_ssl,
        cert_path=args.cert
    )

    print(f"Starting client with {args.threads} threads")
    print(f"Connecting to {args.host}:{args.port} {'with' if not args.no_ssl else 'without'} SSL")

    start_time = time.time()
    run_concurrent_searches(client, args.queries, args.threads)
    end_time = time.time()

    print(f"\nCompleted {len(args.queries)} queries in {(end_time - start_time) * 1000:.2f} ms")


if __name__ == "__main__":
    main()