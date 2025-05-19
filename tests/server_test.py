import os
import socket
import sys
import threading
import time
import tempfile
from typing import Generator, List, Tuple, Any
from contextlib import contextmanager

import pytest
import ssl

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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
from src.server import SearchHandler, ThreadedTCPServer

CONFIG_FILE = "tests/test.conf"
TEST_DATA = "test data\nsome other data\nmore test lines\n"
SERVER_STARTUP_DELAY = 0.5 
TEST_PORT = 0 


@pytest.fixture
def temp_file() -> Generator[str, None, None]:
    """Create a temporary test file with sample data.

    Yields:
        Path to the temporary file.
    """
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp.write(TEST_DATA)
        tmp_path = tmp.name

    time.sleep(0.1) 
    yield tmp_path

    try:
        os.unlink(tmp_path)
    except OSError:
        pass


@pytest.fixture
def real_config() -> Config:
    """Create a test configuration with overrides.

    Returns:
        Config: Test-ready configuration instance.
    """
    config = Config(CONFIG_FILE)
    config.host = "localhost"
    config.port = TEST_PORT
    config.search_algorithm = "inmemory"
    config.reread_on_query = False
    return config


@pytest.fixture
def server_with_real_algorithm(
    real_config: Config, temp_file: str
) -> Generator[ThreadedTCPServer, None, None]:
    """Fixture for a running server with test configuration.

    Args:
        real_config: Pytest fixture providing test config.
        temp_file: Pytest fixture providing test data path.

    Yields:
        ThreadedTCPServer: Running server instance.
    """
    real_config.linux_path = temp_file
    SearchHandler.algorithm_instances = {} 

    server = ThreadedTCPServer(
        (real_config.host, real_config.port), SearchHandler, real_config
    )
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    time.sleep(SERVER_STARTUP_DELAY)
    yield server

    server.shutdown()
    server.server_close()
    server_thread.join(timeout=2)


@contextmanager
def client_socket(server: ThreadedTCPServer) -> Generator[socket.socket, None, None]:
    """Context manager for test client sockets.

    Args:
        server: Server instance to connect to.

    Yields:
        socket: Connected client socket.
    """
    host, port = server.server_address
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if server.config.use_ssl:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.maximum_version = ssl.TLSVersion.TLSv1_3

            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            sock = context.wrap_socket(sock, server_hostname=host)
    sock.connect((host, port))
    sock.settimeout(2)
    yield sock


def send_query_and_get_response(
    client: socket.socket, query: str
) -> Tuple[bytes, bool]:
    """Helper to send a query and get the server response.

    Args:
        client: Connected socket.
        query: Search query string.

    Returns:
        tuple: (response_data, success_status)
    """
    try:
        client.sendall(query.encode() + b"\n")
        time.sleep(0.1)
        return client.recv(1024), True
    except (socket.timeout, ConnectionError):
        return b"", False


class TestSearchHandler:
    """Test suite for SearchHandler functionality."""

    def test_found_query(self, server_with_real_algorithm: ThreadedTCPServer) -> None:
        """Test successful search query."""
        with client_socket(server_with_real_algorithm) as client:
            response, success = send_query_and_get_response(client, "test data")
            assert success, "Communication failed"
            assert response == b"STRING EXISTS\n"

    def test_not_found_query(
        self, server_with_real_algorithm: ThreadedTCPServer
    ) -> None:
        """Test unsuccessful search query."""
        with client_socket(server_with_real_algorithm) as client:
            response, success = send_query_and_get_response(client, "nonexistent")
            assert success, "Communication failed"
            assert response == b"STRING NOT FOUND\n"

    def test_empty_request(self, server_with_real_algorithm: ThreadedTCPServer) -> None:
        """Test empty query handling."""
        with client_socket(server_with_real_algorithm) as client:
            response, success = send_query_and_get_response(client, "")
            assert success, "Communication failed"
            assert response == b"ERROR: Empty request\n"

    def test_oversized_request(
        self, server_with_real_algorithm: ThreadedTCPServer
    ) -> None:
        """Test payload size enforcement."""
        with client_socket(server_with_real_algorithm) as client:
            client.sendall(b"x" * 1500 + b"\n")
            time.sleep(0.1)
            response = client.recv(1024)
            assert response == b"ERROR: Payload too large\n"

    def test_unicode_error(self, server_with_real_algorithm: ThreadedTCPServer) -> None:
        """Test invalid encoding handling."""
        with client_socket(server_with_real_algorithm) as client:
            client.sendall(b"\xff\xfe\xfd\n")
            time.sleep(0.1)
            response = client.recv(1024)
            assert response == b"ERROR: Invalid character encoding\n"


class TestThreadedTCPServer:
    """Test suite for ThreadedTCPServer functionality."""

    def test_init_and_close(self, real_config: Config, temp_file: str) -> None:
        """Test server lifecycle management."""
        real_config.linux_path = temp_file
        server = ThreadedTCPServer(
            (real_config.host, real_config.port), SearchHandler, real_config
        )

        assert server.config == real_config
        assert server._max_workers == real_config.workers

        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.2)

        assert server_thread.is_alive()

        server.shutdown()
        server.server_close()
        server_thread.join(timeout=1)
        assert not server_thread.is_alive()

    def test_address_in_use(self, real_config: Config) -> None:
        """Test port collision handling."""
        server1 = ThreadedTCPServer(
            (real_config.host, TEST_PORT), SearchHandler, real_config
        )
        server_thread = threading.Thread(target=server1.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.2)

        try:
            host, port = server1.server_address
            with pytest.raises(OSError) as excinfo:
                ThreadedTCPServer((host, port), SearchHandler, real_config)

            assert any(
                msg in str(excinfo.value).lower()
                for msg in ["address already in use", "busy"]
            )
        finally:
            server1.shutdown()
            server1.server_close()
            server_thread.join(timeout=1)

    def test_multiple_connections(
        self, real_config: Config, temp_file: str
    ) -> None:
        """Test concurrent connection handling."""
        real_config.linux_path = temp_file
        server = ThreadedTCPServer(
            (real_config.host, real_config.port), SearchHandler, real_config
        )
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(SERVER_STARTUP_DELAY)

        results: List[bool] = []

        def client_task(query: str, expected: str) -> None:
            try:
                with client_socket(server) as client:
                    response, success = send_query_and_get_response(client, query)
                    results.append(success and response == expected.encode() + b"\n")
            except Exception:
                results.append(False)

        threads = []
        for i in range(5):
            query = "test data" if i % 2 == 0 else "nonexistent"
            expected = "STRING EXISTS" if i % 2 == 0 else "STRING NOT FOUND"
            thread = threading.Thread(target=client_task, args=(query, expected))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        server.shutdown()
        server.server_close()
        server_thread.join(timeout=1)

        assert all(results), "Some connections failed"
        assert len(results) == 5, "Missing results"


class TestAlgorithmSelection:
    """Test suite for algorithm selection functionality."""

    @pytest.mark.parametrize(
        "algorithm_name",
        [
            "simple",
            "inmemory",
            "binary",
            "hash",
            "regex",
            "bloom",
            "boyermoore",
            "rabinkarp",
            "kmp",
        ],
    )
    def test_algorithm_implementation(
        self, algorithm_name: str, real_config: Config, temp_file: str
    ) -> None:
        """Test all supported search algorithms.

        Args:
            algorithm_name: Name of algorithm to test.
            real_config: Pytest fixture providing test config.
            temp_file: Pytest fixture providing test data path.
        """
        real_config.search_algorithm = algorithm_name
        real_config.linux_path = temp_file
        SearchHandler.algorithm_instances = {}

        server = ThreadedTCPServer(
            (real_config.host, real_config.port), SearchHandler, real_config
        )
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(SERVER_STARTUP_DELAY)

        try:
            with client_socket(server) as client:
                response, success = send_query_and_get_response(client, "test data")
                assert success, "Communication failed"
                assert response == b"STRING EXISTS\n", (
                    f"Algorithm {algorithm_name} failed basic test"
                )
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=2)


class TestIntegration:
    """Comprehensive integration test suite."""

    def test_full_workflow(self, real_config: Config, temp_file: str) -> None:
        """Test complete server workflow with multiple operations.

        Args:
            real_config: Pytest fixture providing test config.
            temp_file: Pytest fixture providing test data path.
        """
        with open(temp_file, "w") as f:
            f.write("test line 1\ntest data line\nsome random text\nLAST LINE\n")

        real_config.linux_path = temp_file
        real_config.search_algorithm = "inmemory"
        SearchHandler.algorithm_instances = {}

        server = ThreadedTCPServer(
            (real_config.host, real_config.port), SearchHandler, real_config
        )
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(SERVER_STARTUP_DELAY)

        try:
            test_cases = [
                ("test data line", b"STRING EXISTS\n"),
                ("LAST LINE", b"STRING EXISTS\n"),
                ("nonexistent", b"STRING NOT FOUND\n"),
                ("", b"ERROR: Empty request\n"),
            ]

            for query, expected in test_cases:
                with client_socket(server) as client:
                    response, success = send_query_and_get_response(client, query)
                    assert success, f"Failed on query: {query}"
                    assert response == expected, f"Unexpected response for: {query}"
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=2)