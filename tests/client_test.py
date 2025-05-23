import pytest
import socket
import ssl
from unittest.mock import patch, MagicMock
from src.client import SearchClient
from typing import Generator

@pytest.fixture
def mock_socket() -> Generator[MagicMock, None, None]:
    """
    Fixture to mock the socket module.
    """
    with patch('socket.socket') as mock_sock:
        yield mock_sock


@pytest.fixture
def mock_ssl_context() -> Generator[MagicMock, None, None]:
    """
    Fixture to mock the SSLContext class.
    """
    with patch('ssl.SSLContext') as mock_ctx:
        yield mock_ctx


@pytest.fixture
def basic_client() -> SearchClient:
    """
    Fixture to create a basic SearchClient instance without SSL.
    """
    return SearchClient(host="localhost", port=8443, use_ssl=False)


@pytest.fixture
def ssl_client() -> SearchClient:
    """
    Fixture to create a SearchClient instance with SSL enabled.
    """
    return SearchClient(host="localhost", port=8443, use_ssl=True)


@pytest.fixture
def ssl_client_with_cert() -> SearchClient:
    """
    Fixture to create a SearchClient instance with SSL and a certificate.
    """
    return SearchClient(host="localhost", port=8443, use_ssl=True)


def test_client_initialization() -> None:
    """
    Test the initialization of the SearchClient class.
    """
    client = SearchClient(host="example.com", port=1234, use_ssl=True)
    assert client.host == "example.com"
    assert client.port == 1234
    assert client.use_ssl is True


def test_create_connection_basic(basic_client: SearchClient, mock_socket: MagicMock) -> None:
    """
    Test creating a basic connection without SSL.
    """
    mock_socket_instance = MagicMock()
    mock_socket.return_value = mock_socket_instance

    sock = basic_client.create_connection()

    mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
    mock_socket_instance.connect.assert_called_once_with(("localhost", 8443))
    assert sock == mock_socket_instance


def test_create_connection_ssl(ssl_client: SearchClient, mock_socket: MagicMock, mock_ssl_context: MagicMock) -> None:
    """
    Test creating a connection with SSL enabled.
    """
    mock_socket_instance = MagicMock()
    mock_ssl_instance = MagicMock()
    mock_wrapped_socket = MagicMock()

    mock_socket.return_value = mock_socket_instance
    mock_ssl_context.return_value = mock_ssl_instance
    mock_ssl_instance.wrap_socket.return_value = mock_wrapped_socket

    sock = ssl_client.create_connection()

    mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
    mock_ssl_context.assert_called_once_with(ssl.PROTOCOL_TLS_CLIENT)
    assert mock_ssl_instance.minimum_version == ssl.TLSVersion.TLSv1_2
    assert mock_ssl_instance.maximum_version == ssl.TLSVersion.TLSv1_3
    mock_ssl_instance.wrap_socket.assert_called_once_with(mock_socket_instance, server_hostname="localhost")
    mock_wrapped_socket.connect.assert_called_once_with(("localhost", 8443))
    assert sock == mock_wrapped_socket


def test_run_concurrent_searches(capsys: pytest.CaptureFixture, basic_client: SearchClient) -> None:
    """
    Test running concurrent searches with multiple queries.
    """
    queries = ["query1", "query2", "query3"]

    with patch.object(basic_client, 'search') as mock_search:
        mock_search.side_effect = ["result1", "result2", ValueError("test error")]

        from src.client import run_concurrent_searches
        run_concurrent_searches(basic_client, queries, num_threads=3)

        captured = capsys.readouterr()
        output = captured.out

        assert "Query 'query1' => result1" in output
        assert "Query 'query2' => result2" in output
        assert "Query 'query3' generated an exception: test error" in output


def test_main_with_ssl(capsys: pytest.CaptureFixture) -> None:
    """
    Test the main function with SSL enabled.
    """
    test_args = [
        "--host", "testhost",
        "--port", "1234",
        "--queries", "q1", "q2", "q3",
        "--threads", "5"
    ]

    with patch('argparse.ArgumentParser.parse_args') as mock_args, \
         patch('src.client.SearchClient') as mock_client, \
         patch('src.client.run_concurrent_searches') as mock_run, \
         patch('time.time') as mock_time:

        mock_args.return_value = MagicMock(
            host="testhost",
            port=1234,
            no_ssl=False,
            cert=None,
            queries=["q1", "q2", "q3"],
            threads=5
        )
        mock_time.side_effect = [1000, 1002]  # start and end times

        from src.client import main
        main()

        captured = capsys.readouterr()
        assert "Starting client with 5 threads" in captured.out
        assert "Connecting to testhost:1234 with SSL" in captured.out
        assert "Completed 3 queries in 2000.00 ms" in captured.out
        mock_client.assert_called_once_with(
            host="testhost",
            port=1234,
            use_ssl=True,
            cert_path=None
        )
        mock_run.assert_called_once_with(mock_client.return_value, ["q1", "q2", "q3"], 5)


def test_main_without_ssl(capsys: pytest.CaptureFixture) -> None:
    """
    Test the main function without SSL.
    """
    test_args = [
        "--host", "testhost",
        "--port", "1234",
        "--no-ssl",
        "--queries", "q1"
    ]

    with patch('argparse.ArgumentParser.parse_args') as mock_args, \
         patch('src.client.SearchClient') as mock_client:

        mock_args.return_value = MagicMock(
            host="testhost",
            port=1234,
            no_ssl=True,
            cert=None,
            queries=["q1"],
            threads=10
        )

        from src.client import main, SearchClient
        main()

        captured = capsys.readouterr()
        assert "Connecting to testhost:1234 without SSL" in captured.out
        mock_client.assert_called_once_with(
            host="testhost",
            port=1234,
            use_ssl=False,
            cert_path=None
        )