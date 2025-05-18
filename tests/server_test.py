import unittest
from unittest.mock import patch, MagicMock, mock_open, call
import socket
import ssl
import socketserver
import threading
import queue
import time
import datetime
from src.config.config import Config
from src.server.server import (
    SearchHandler,
    ThreadPoolMixIn,
    ThreadedTCPServer,
    run_server,
    MAX_PAYLOAD_SIZE,
    DEFAULT_THREAD_POOL_SIZE,
    REQUEST_QUEUE_SIZE
)

class TestSearchHandler(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock(spec=Config)
        self.config.use_ssl = False
        self.config.search_algorithm = 'inmemory'
        self.config.linux_path = '/test/path'
        self.config.reread_on_query = False
        self.config.case_sensitive = False
        self.config.debug = False
        self.config.logger = MagicMock()
        
        self.request = MagicMock()
        self.client_address = ('127.0.0.1', 12345)
        self.server = MagicMock()
        self.server.config = self.config
        
        # Reset class-level instances
        SearchHandler.algorithm_instances = {}

    def test_setup_without_ssl(self):
        handler = SearchHandler()
        handler.request = self.request
        handler.client_address = self.client_address
        handler.server = self.server
        
        handler.setup()
        
        self.assertIsNotNone(handler.search_algo)
        self.assertEqual(len(SearchHandler.algorithm_instances), 1)
        self.assertIn('inmemory_/test/path', SearchHandler.algorithm_instances)

    @patch('ssl.SSLContext')
    def test_setup_with_ssl(self, mock_ssl_context):
        self.config.use_ssl = True
        self.config.ssl_cert = '/path/to/cert'
        self.config.ssl_key = '/path/to/key'
        
        mock_context = MagicMock()
        mock_ssl_context.return_value = mock_context
        
        handler = SearchHandler()
        handler.request = self.request
        handler.client_address = self.client_address
        handler.server = self.server
        
        handler.setup()
        
        mock_ssl_context.assert_called_once_with(ssl.PROTOCOL_TLS_SERVER)
        mock_context.load_cert_chain.assert_called_once_with(
            certfile='/path/to/cert', keyfile='/path/to/key'
        )
        mock_context.wrap_socket.assert_called_once_with(self.request, server_side=True)

    def test_handle_empty_request(self):
        handler = SearchHandler()
        handler.request = MagicMock()
        handler.request.recv.side_effect = [b'']
        handler.client_address = self.client_address
        handler.server = self.server
        
        handler.setup()
        handler.handle()
        
        self.config.logger.info.assert_called_with(
            "[127.0.0.1:12345] Connection closed without any requests"
        )

    def test_handle_single_request(self):
        handler = SearchHandler()
        handler.request = MagicMock()
        handler.request.recv.side_effect = [b'test query\n', b'']
        handler.client_address = self.client_address
        handler.server = self.server
        
        mock_algo = MagicMock()
        mock_algo.search.return_value = True
        handler.search_algo = mock_algo
        
        handler.handle()
        
        mock_algo.search.assert_called_once_with('test query')
        handler.request.sendall.assert_called_once_with(b"STRING EXISTS\n")
        self.config.logger.info.assert_any_call(
            "[127.0.0.1:12345] Request #1: Search query 'test query' (11 bytes)"
        )
        self.config.logger.info.assert_any_call(
            "[127.0.0.1:12345] Response #1: FOUND (took 0.00ms)"
        )

    def test_handle_large_payload(self):
        handler = SearchHandler()
        handler.request = MagicMock()
        # Send a payload that's too large
        large_payload = b'A' * (MAX_PAYLOAD_SIZE + 1)
        handler.request.recv.side_effect = [large_payload[:MAX_PAYLOAD_SIZE], large_payload[MAX_PAYLOAD_SIZE:]]
        handler.client_address = self.client_address
        handler.server = self.server
        
        handler.setup()
        handler.handle()
        
        self.config.logger.error.assert_called_with(
            "[127.0.0.1:12345] Request exceeds maximum payload size of 1024 bytes"
        )
        handler.request.sendall.assert_called_once_with(b"ERROR: Payload too large\n")

    def test_handle_connection_reset_error(self):
        handler = SearchHandler()
        handler.request = MagicMock()
        handler.request.recv.side_effect = ConnectionResetError()
        handler.client_address = self.client_address
        handler.server = self.server
        
        handler.setup()
        handler.handle()
        
        self.config.logger.warning.assert_called_with(
            "[127.0.0.1:12345] Connection reset by peer after 0 requests"
        )

class TestThreadPoolMixIn(unittest.TestCase):
    def setUp(self):
        self.mixin = ThreadPoolMixIn()
        self.mixin.finish_request = MagicMock()
        self.mixin.close_request = MagicMock()
        
    def test_process_request(self):
        mock_request = MagicMock()
        client_address = ('127.0.0.1', 12345)
        
        self.mixin.process_request(mock_request, client_address)
        
        # Check if the request was put in the queue
        self.assertEqual(self.mixin._requests.qsize(), 1)
        
    def test_process_request_when_shutdown(self):
        self.mixin._shutdown = True
        mock_request = MagicMock()
        client_address = ('127.0.0.1', 12345)
        
        self.mixin.process_request(mock_request, client_address)
        
        # Should not process the request
        self.assertEqual(self.mixin._requests.qsize(), 0)
        
    def test_process_request_when_queue_full(self):
        # Fill the queue
        for _ in range(REQUEST_QUEUE_SIZE):
            self.mixin._requests.put((MagicMock(), ('127.0.0.1', 12345)))
        
        mock_request = MagicMock()
        client_address = ('127.0.0.1', 12345)
        
        self.mixin.process_request(mock_request, client_address)
        
        # Should have tried to send busy message
        mock_request.sendall.assert_called_once_with(b"ERROR: Server too busy\n")
        self.mixin.close_request.assert_called_once_with(mock_request)

    @patch('concurrent.futures.ThreadPoolExecutor')
    def test_server_close(self, mock_executor):
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance
        
        mixin = ThreadPoolMixIn()
        mixin._shutdown = False
        mixin._requests = MagicMock()
        mixin._request_processor = MagicMock()
        mixin._thread_pool = mock_executor_instance
        
        mixin.server_close()
        
        self.assertTrue(mixin._shutdown)
        mixin._requests.put.assert_called_once_with((None, None), block=False)
        mock_executor_instance.shutdown.assert_called_once_with(wait=False)

class TestThreadedTCPServer(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock(spec=Config)
        self.config.workers = 10
        
    def test_init(self):
        server = ThreadedTCPServer(('127.0.0.1', 8080), SearchHandler, self.config)
        
        self.assertEqual(server._max_workers, 10)
        self.assertEqual(server.config, self.config)
        
    def test_finish_request(self):
        server = ThreadedTCPServer(('127.0.0.1', 8080), SearchHandler, self.config)
        mock_request = MagicMock()
        client_address = ('127.0.0.1', 12345)
        
        with patch.object(SearchHandler, '__init__', return_value=None) as mock_handler_init:
            server.finish_request(mock_request, client_address)
            
            mock_handler_init.assert_called_once_with(
                mock_request, client_address, server, config=self.config
            )

class TestRunServer(unittest.TestCase):
    @patch('server.ThreadedTCPServer')
    @patch('server.Config')
    @patch('socket.gethostname')
    @patch('datetime.datetime')
    @patch('platform.system')
    @patch('platform.release')
    @patch('psutil.cpu_count')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_run_server(
        self, mock_disk_usage, mock_virtual_memory, mock_cpu_count,
        mock_release, mock_system, mock_datetime, mock_gethostname,
        mock_config, mock_server
    ):
        # Setup mocks
        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.host = 'localhost'
        mock_config_instance.port = 8080
        mock_config_instance.use_ssl = False
        mock_config_instance.search_algorithm = 'inmemory'
        mock_config_instance.workers = 10
        mock_config_instance.linux_path = '/test/path'
        mock_config_instance.debug = True
        mock_config_instance.version = '1.0.0'
        mock_config_instance.build_date = '2023-01-01'
        
        mock_gethostname.return_value = 'testhost'
        
        mock_now = MagicMock()
        mock_now.strftime.return_value = '2023-01-01 12:00:00'
        mock_datetime.now.return_value = mock_now
        
        mock_system.return_value = 'Linux'
        mock_release.return_value = '5.4.0'
        mock_cpu_count.return_value = 8
        mock_memory = MagicMock()
        mock_memory.total = 16 * 1024**3
        mock_memory.available = 8 * 1024**3
        mock_virtual_memory.return_value = mock_memory
        mock_disk = MagicMock()
        mock_disk.total = 500 * 1024**3
        mock_disk.free = 200 * 1024**3
        mock_disk_usage.return_value = mock_disk
        
        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance
        
        # Simulate KeyboardInterrupt to stop serve_forever
        mock_server_instance.serve_forever.side_effect = KeyboardInterrupt()
        
        # Run the server
        run_server('test_config.conf')
        
        # Verify calls
        mock_config.assert_called_once_with('test_config.conf')
        mock_server.assert_called_once_with(
            ('localhost', 8080), SearchHandler, mock_config_instance
        )
        
        # Verify logging calls
        expected_log_calls = [
            call.info('    ┌────────────────────────────────────────────────────────────┐'),
            call.info('    │                     SEARCH SERVER v1.0.0                   │'),
            call.info('    ├────────────────────────────────────────────────────────────┤'),
            call.info('     Host: localhost          Port: 8080    '),
            call.info('     SSL: ✗                    Started: 2023-01-01 12:00:00 '),
            call.info('     Algorithm: inmemory      Workers: 10                   '),
            call.info('    └────────────────────────────────────────────────────────────┘'),
            call.info('    ┌────────────────────────────────────────────────────────────┐'),
            call.info('Server configuration details:'),
            call.info('  - Search Path: /test/path'),
            call.info('  - Request Queue Size: 1000'),
            call.info('System information:'),
            call.info('  - OS: Linux 5.4.0'),
            call.info('  - CPU: 8 cores'),
            call.info('  - Memory: 16GB total, 8GB available'),
            call.info('  - Disk: 500GB total, 200GB free on search path'),
            call.warning('[2023-01-01 12:00:00] Search server started successfully on localhost:8080'),
            call.warning('Waiting for incoming connections...'),
        ]
        
        # Check that all expected logging calls were made
        for expected_call in expected_log_calls:
            self.assertIn(expected_call, mock_config_instance.logger.method_calls)

if __name__ == '__main__':
    unittest.main()