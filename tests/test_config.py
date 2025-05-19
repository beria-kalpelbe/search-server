import pytest
import tempfile
import os
import configparser
import logging
from unittest.mock import MagicMock
from src.config.config import Config


@pytest.fixture
def config_fixture():
    """Fixture that creates a temporary config file for testing"""
    temp_dir = tempfile.TemporaryDirectory()
    config_file = os.path.join(temp_dir.name, "test_config.conf")
    
    config_content = """
[SERVER]
HOST = localhost
PORT = 8080
USE_SSL = False
SSL_CERT = certs/server.crt
SSL_KEY = certs/server.key
WORKERS = 4
DEBUG = True

[SEARCH]
LINUX_PATH = /usr/bin
ALGORITHM = binary
REREAD_ON_QUERY = False
CASE_SENSITIVE = True

[LOGGING]
level = INFO
file = /var/log/test.log
"""
    with open(config_file, 'w') as f:
        f.write(config_content)
        
    ssl_cert = os.path.join(temp_dir.name, "cert.pem")
    ssl_key = os.path.join(temp_dir.name, "key.pem")
    
    yield {
        'temp_dir': temp_dir,
        'config_file': config_file,
        'ssl_cert': ssl_cert,
        'ssl_key': ssl_key
    }
    
    logging.getLogger("SearchServer").handlers = []
    temp_dir.cleanup()


def test_init_with_valid_config(config_fixture):
    """Test initialization with a valid config file"""
    config = Config(config_fixture['config_file'])
    
    assert config.host == "localhost"
    assert config.port == 8080
    assert config.use_ssl is False
    assert config.ssl_cert == "certs/server.crt"
    assert config.ssl_key == "certs/server.key"
    assert config.workers == 4
    assert config.debug is True
    
    assert config.linux_path == "/usr/bin"
    assert config.search_algorithm == "binary"
    assert config.reread_on_query is False
    assert config.case_sensitive is True
    
    assert config.log_level == "INFO"
    assert config.log_file == "/var/log/test.log"


def test_init_with_missing_file():
    """Test initialization with missing config file"""
    with pytest.raises(FileNotFoundError):
        Config("nonexistent.conf")


def test_validate_config_missing_linux_path(config_fixture):
    """Test validation when linux_path is missing"""
    config = configparser.ConfigParser()
    config.read(config_fixture['config_file'])
    config.remove_option('SEARCH', 'LINUX_PATH')
    with open(config_fixture['config_file'], 'w') as f:
        config.write(f)
        
    with pytest.raises(ValueError):
        Config(config_fixture['config_file'])


def test_validate_config_ssl(config_fixture):
    """Test SSL validation"""
    ssl_cert = config_fixture['ssl_cert']
    ssl_key = config_fixture['ssl_key']
    
    with open(ssl_cert, 'w') as f:
        f.write("test cert")
    with open(ssl_key, 'w') as f:
        f.write("test key")
        
    config = configparser.ConfigParser()
    config.read(config_fixture['config_file'])
    config['SERVER']['USE_SSL'] = 'True'
    config['SERVER']['SSL_CERT'] = ssl_cert
    config['SERVER']['SSL_KEY'] = ssl_key
    with open(config_fixture['config_file'], 'w') as f:
        config.write(f)
        
    cfg = Config(config_fixture['config_file'])
    assert cfg.use_ssl is True
    
    os.unlink(ssl_cert)
    with pytest.raises(ValueError):
        Config(config_fixture['config_file'])
        
    with open(ssl_cert, 'w') as f:
        f.write("test cert")
    os.unlink(ssl_key)
    with pytest.raises(ValueError):
        Config(config_fixture['config_file'])


def test_initiate_logger(config_fixture, monkeypatch, caplog):
    """Test logger initialization"""
    # Setup mocks
    mock_logger = MagicMock()
    mock_file_handler = MagicMock()
    mock_stream_handler = MagicMock()
    
    monkeypatch.setattr('logging.getLogger', lambda name=None: mock_logger if name != "root" else logging.getLogger(name))
    monkeypatch.setattr('logging.handlers.RotatingFileHandler', 
                       lambda *args, **kwargs: mock_file_handler)
    monkeypatch.setattr('logging.StreamHandler', 
                       lambda *args, **kwargs: mock_stream_handler)
    
    log_file = os.path.join(config_fixture['temp_dir'].name, "test.log")
    config = configparser.ConfigParser()
    config.read(config_fixture['config_file'])
    config['LOGGING']['file'] = log_file
    with open(config_fixture['config_file'], 'w') as f:
        config.write(f)
    
    config = Config(config_fixture['config_file'])
    config._initiate_logger()
    
    mock_logger.setLevel.assert_called_with(logging.INFO)
    
    assert mock_logger.addHandler.call_count == 4 


def test_initiate_logger_file_error(config_fixture, monkeypatch):
    """Test logger initialization when file creation fails"""
    mock_logger = MagicMock()
    monkeypatch.setattr('logging.getLogger', lambda name=None: mock_logger)
    
    config = configparser.ConfigParser()
    config.read(config_fixture['config_file'])
    config['LOGGING']['file'] = "/invalid/path/test.log"
    with open(config_fixture['config_file'], 'w') as f:
        config.write(f)
        
    config = Config(config_fixture['config_file'])
    config._initiate_logger()
    
    mock_logger.error.assert_called()
    mock_logger.warning.assert_called_with("Continuing with console logging only")


def test_create_log_file(config_fixture):
    """Test log file creation"""
    log_file = os.path.join(config_fixture['temp_dir'].name, "test_logs", "test.log")
    
    config = Config(config_fixture['config_file'])
    config._create_log_file(log_file)
    
    assert os.path.exists(log_file)
    
    config._create_log_file(log_file)


def test_get_method(config_fixture):
    """Test the get method for config values"""
    config = Config(config_fixture['config_file'])
    
    assert config.get('SERVER', 'HOST') == 'localhost'
    assert config.get('SEARCH', 'ALGORITHM') == 'binary'
    
    with pytest.raises(KeyError):
        config.get('NONEXISTENT', 'KEY')


def test_save_method(config_fixture):
    """Test saving config to file"""
    config = Config(config_fixture['config_file'])
    new_file = os.path.join(config_fixture['temp_dir'].name, "new_config.conf")
    
    config.host = "localhost"
    config.save(new_file)
    
    new_config = Config(new_file)
    assert new_config.host == "localhost"