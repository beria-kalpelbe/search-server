import os
import socket
import sys
import threading
import time
import tempfile
from typing import Generator, List, Tuple, Any
from contextlib import contextmanager
from pathlib import Path

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

# Test constants
TEST_DATA = "test data\nsome other data\nmore test lines\n"
SERVER_STARTUP_TIMEOUT = 2.0
SERVER_SHUTDOWN_TIMEOUT = 3.0


def get_free_port() -> int:
    """Get a free port for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        return s.getsockname()[1]


@contextmanager
def wait_for_server_ready(server: ThreadedTCPServer, timeout: float = SERVER_STARTUP_TIMEOUT):
    """Wait for server to be ready to accept connections."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test_sock:
                test_sock.settimeout(0.1)
                result = test_sock.connect_ex(server.server_address)
                if result == 0:
                    yield
                    return
        except (socket.error, OSError):
            pass
        time.sleep(0.05)
    
    raise TimeoutError(f"Server failed to start within {timeout} seconds")


@pytest.fixture(scope="function")
def temp_file() -> Generator[Path, None, None]:
    """Create a temporary test file with sample data."""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as tmp:
        tmp.write(TEST_DATA)
        tmp.flush()
        tmp_path = Path(tmp.name)

    try:
        yield tmp_path
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@pytest.fixture(scope="function")
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture(scope="function")
def config_file(temp_dir: Path) -> Path:
    """Create a test configuration file."""
    config_file = temp_dir / "test_config.conf"
    data_file = temp_dir / "test_data.txt"
    log_file = temp_dir / "test.log"
    
    # Create empty data file
    data_file.touch()
    
    config_content = f"""[SERVER]
HOST = localhost
PORT = {get_free_port()}
USE_SSL = false
SSL_CERT = 
SSL_KEY = 
WORKERS = 4
DEBUG = true

[SEARCH]
LINUX_PATH = {data_file}
ALGORITHM = simple
REREAD_ON_QUERY = false
CASE_SENSITIVE = true

[LOGGING]
LEVEL = INFO
FILE = {log_file}
"""
    
    config_file.write_text(config_content)
    return config_file


@pytest.fixture(scope="function")
def real_config(config_file: Path, temp_file: Path) -> Config:
    """Create a test configuration with overrides."""
    config = Config(str(config_file))
    config.host = "localhost"
    config.port = get_free_port()
    config.linux_path = str(temp_file)
    config.search_algorithm = "inmemory"
    config.reread_on_query = False
    return config


@pytest.fixture(scope="function")
def server_with_real_algorithm(real_config: Config) -> Generator[ThreadedTCPServer, None, None]:
    """Fixture for a running server with test configuration."""
    SearchHandler.algorithm_instances = {}

    server = ThreadedTCPServer(
        (real_config.host, real_config.port), SearchHandler, real_config
    )
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        with wait_for_server_ready(server):
            yield server
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=SERVER_SHUTDOWN_TIMEOUT)
        if server_thread.is_alive():
            pytest.fail("Server thread failed to shutdown cleanly")


@pytest.fixture(autouse=True)
def cleanup_algorithm_instances():
    """Auto-cleanup fixture to ensure algorithm instances are cleaned up."""
    yield
    SearchHandler.algorithm_instances = {}


@contextmanager
def client_socket(server: ThreadedTCPServer) -> Generator[socket.socket, None, None]:
    """Context manager for test client sockets."""
    host, port = server.server_address
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
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
    finally:
        try:
            sock.close()
        except:
            pass


def send_query_and_get_response(client: socket.socket, query: str) -> Tuple[bytes, bool]:
    """Helper to send a query and get the server response."""
    try:
        client.sendall(query.encode() + b"\n")
        time.sleep(0.1)
        return client.recv(1024), True
    except (socket.timeout, ConnectionError, OSError):
        return b"", False


class TestSearchHandler:
    """Test suite for SearchHandler functionality."""

    def test_found_query(self, server_with_real_algorithm: ThreadedTCPServer) -> None:
        """Test successful search query."""
        with client_socket(server_with_real_algorithm) as client:
            response, success = send_query_and_get_response(client, "test data")
            assert success, "Communication failed"
            assert response == b"STRING EXISTS\n"

    def test_not_found_query(self, server_with_real_algorithm: ThreadedTCPServer) -> None:
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

    def test_oversized_request(self, server_with_real_algorithm: ThreadedTCPServer) -> None:
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

    def test_init_and_close(self, real_config: Config) -> None:
        """Test server lifecycle management."""
        server = ThreadedTCPServer(
            (real_config.host, real_config.port), SearchHandler, real_config
        )

        assert server.config == real_config
        assert server._max_workers == real_config.workers

        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            with wait_for_server_ready(server):
                assert server_thread.is_alive()
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=SERVER_SHUTDOWN_TIMEOUT)
            assert not server_thread.is_alive()

    def test_address_in_use(self, real_config: Config) -> None:
        """Test port collision handling."""
        # Use a specific port for this test
        test_port = get_free_port()
        server1 = ThreadedTCPServer(
            (real_config.host, test_port), SearchHandler, real_config
        )
        server_thread = threading.Thread(target=server1.serve_forever, daemon=True)
        server_thread.start()

        try:
            with wait_for_server_ready(server1):
                with pytest.raises(OSError) as excinfo:
                    ThreadedTCPServer((real_config.host, test_port), SearchHandler, real_config)

                assert any(
                    msg in str(excinfo.value).lower()
                    for msg in ["address already in use", "busy"]
                )
        finally:
            server1.shutdown()
            server1.server_close()
            server_thread.join(timeout=SERVER_SHUTDOWN_TIMEOUT)

    def test_multiple_connections(self, real_config: Config) -> None:
        """Test concurrent connection handling."""
        server = ThreadedTCPServer(
            (real_config.host, real_config.port), SearchHandler, real_config
        )
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        results: List[bool] = []

        def client_task(query: str, expected: str) -> None:
            try:
                with client_socket(server) as client:
                    response, success = send_query_and_get_response(client, query)
                    results.append(success and response == expected.encode() + b"\n")
            except Exception:
                results.append(False)

        try:
            with wait_for_server_ready(server):
                threads = []
                for i in range(5):
                    query = "test data" if i % 2 == 0 else "nonexistent"
                    expected = "STRING EXISTS" if i % 2 == 0 else "STRING NOT FOUND"
                    thread = threading.Thread(target=client_task, args=(query, expected))
                    threads.append(thread)
                    thread.start()

                for thread in threads:
                    thread.join()
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=SERVER_SHUTDOWN_TIMEOUT)

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
            "grep"
        ],
    )
    def test_algorithm_implementation(self, algorithm_name: str, real_config: Config) -> None:
        """Test all supported search algorithms."""
        real_config.search_algorithm = algorithm_name
        SearchHandler.algorithm_instances = {}

        server = ThreadedTCPServer(
            (real_config.host, real_config.port), SearchHandler, real_config
        )
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            with wait_for_server_ready(server):
                with client_socket(server) as client:
                    response, success = send_query_and_get_response(client, "test data")
                    assert success, f"Communication failed for {algorithm_name}"
                    assert response == b"STRING EXISTS\n", (
                        f"Algorithm {algorithm_name} failed basic test"
                    )
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=SERVER_SHUTDOWN_TIMEOUT)


class TestIntegration:
    """Comprehensive integration test suite."""

    def test_full_workflow(self, real_config: Config, temp_file: Path) -> None:
        """Test complete server workflow with multiple operations."""
        # Write specific test data
        temp_file.write_text("test line 1\ntest data line\nsome random text\nLAST LINE\n")
        
        real_config.linux_path = str(temp_file)
        real_config.search_algorithm = "inmemory"
        SearchHandler.algorithm_instances = {}

        server = ThreadedTCPServer(
            (real_config.host, real_config.port), SearchHandler, real_config
        )
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            with wait_for_server_ready(server):
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
            server_thread.join(timeout=SERVER_SHUTDOWN_TIMEOUT)