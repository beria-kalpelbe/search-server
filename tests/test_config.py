import pytest
import tempfile
import os
import configparser
import logging
from unittest.mock import MagicMock, patch
from src.config.config import Config, ConfigError, ConfigValidationError, ConfigFileError


@pytest.fixture
def temp_dir():
    """Fixture that creates a temporary directory for testing"""
    temp_dir = tempfile.TemporaryDirectory()
    yield temp_dir
    temp_dir.cleanup()


@pytest.fixture
def valid_config_file(temp_dir):
    """Fixture that creates a valid config file for testing"""
    config_file = os.path.join(temp_dir.name, "test_config.conf")
    mock_bin_dir = os.path.join(temp_dir.name, "mock_bin")
    os.makedirs(mock_bin_dir)
    open(f"{mock_bin_dir}/data.txt", 'w').close()
    
    config_content = f"""
[SERVER]
PORT = 8080
USE_SSL = false
SSL_CERT = 
SSL_KEY = 
WORKERS = 4
DEBUG = true

[SEARCH]
LINUX_PATH = {f"{mock_bin_dir}/data.txt"}
ALGORITHM = simple
REREAD_ON_QUERY = false
CASE_SENSITIVE = true

[LOGGING]
LEVEL = INFO
FILE = {os.path.join(temp_dir.name, "test.log")}
"""
    with open(config_file, 'w') as f:
        f.write(config_content)
        
    return config_file


@pytest.fixture
def ssl_config_file(temp_dir):
    """Fixture that creates a config file with SSL enabled"""
    config_file = os.path.join(temp_dir.name, "ssl_config.conf")
    mock_bin_dir = os.path.join(temp_dir.name, "mock_bin")
    os.makedirs(mock_bin_dir)
    open(f"{mock_bin_dir}/data.txt", 'w').close()
    
    # Create SSL certificate and key files
    ssl_cert = os.path.join(temp_dir.name, "server.crt")
    ssl_key = os.path.join(temp_dir.name, "server.key")
    with open(ssl_cert, 'w') as f:
        f.write("mock certificate")
    with open(ssl_key, 'w') as f:
        f.write("mock private key")
    open(f"{mock_bin_dir}/data.txt", 'w').close()
    
    config_content = f"""
[SERVER]
HOST = 192.168.1.100
PORT = 8443
USE_SSL = true
SSL_CERT = {ssl_cert}
SSL_KEY = {ssl_key}
WORKERS = 8
DEBUG = false

[SEARCH]
LINUX_PATH = {f"{mock_bin_dir}/data.txt"}
ALGORITHM = regex
REREAD_ON_QUERY = true
CASE_SENSITIVE = false

[LOGGING]
LEVEL = DEBUG
FILE = 
"""
    with open(config_file, 'w') as f:
        f.write(config_content)
        
    return config_file


def test_init_with_valid_config(valid_config_file):
    """Test initialization with a valid config file"""
    config = Config(valid_config_file)
    
    assert config.host == "localhost"
    assert config.port == 8080
    assert config.use_ssl is False
    assert config.ssl_cert is None
    assert config.ssl_key is None
    assert config.workers == 4
    assert config.debug is True
    
    assert config.search_algorithm == "simple"
    assert config.reread_on_query is False
    assert config.case_sensitive is True
    
    assert config.log_level == "INFO"
    assert config.log_file is not None
    assert config.logger is not None


def test_init_with_ssl_config(ssl_config_file):
    """Test initialization with SSL enabled"""
    config = Config(ssl_config_file)
    
    assert config.host == "localhost"
    assert config.port == 8443
    assert config.use_ssl is True
    assert config.ssl_cert is not None
    assert config.ssl_key is not None
    assert config.workers == 8
    assert config.debug is False
    
    assert config.search_algorithm == "regex"
    assert config.reread_on_query is True
    assert config.case_sensitive is False
    
    assert config.log_level == "DEBUG"
    assert config.log_file is None


def test_init_with_missing_file():
    """Test initialization with missing config file"""
    with pytest.raises(ConfigFileError, match="Configuration file 'nonexistent.conf' not found"):
        Config("nonexistent.conf")


def test_init_with_unreadable_file(temp_dir):
    """Test initialization with unreadable config file"""
    config_file = os.path.join(temp_dir.name, "unreadable.conf")
    with open(config_file, 'w') as f:
        f.write("[SERVER]\nHOST=localhost")
    
    # Make file unreadable
    os.chmod(config_file, 0o000)
    
    try:
        with pytest.raises(ConfigFileError, match="is not readable"):
            Config(config_file)
    finally:
        # Restore permissions for cleanup
        os.chmod(config_file, 0o644)


def test_init_with_malformed_config(temp_dir):
    """Test initialization with malformed config file"""
    config_file = os.path.join(temp_dir.name, "malformed.conf")
    with open(config_file, 'w') as f:
        f.write("This is not a valid INI file\n[BROKEN")
    
    with pytest.raises(ConfigFileError, match="Failed to parse configuration file"):
        Config(config_file)


def test_missing_required_sections(temp_dir):
    """Test initialization with missing required sections"""
    config_file = os.path.join(temp_dir.name, "incomplete.conf")
    with open(config_file, 'w') as f:
        f.write("[SERVER]\nHOST=localhost\n")
    
    with pytest.raises(ConfigFileError, match="Missing required sections"):
        Config(config_file)


def test_invalid_data_types(temp_dir):
    """Test validation with invalid data types"""
    config_file = os.path.join(temp_dir.name, "invalid_types.conf")
    mock_bin_dir = os.path.join(temp_dir.name, "mock_bin")
    os.makedirs(mock_bin_dir)
    open(f"{mock_bin_dir}/data.txt", 'w').close()
    # Invalid port (non-integer)
    config_content = f"""
[SERVER]
PORT = not_a_number
USE_SSL = false
WORKERS = 4
DEBUG = true

[SEARCH]
LINUX_PATH = {mock_bin_dir}/data.txt
ALGORITHM = simple
REREAD_ON_QUERY = false
CASE_SENSITIVE = true

[LOGGING]
LEVEL = INFO
"""
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    with pytest.raises(ConfigValidationError, match="Invalid integer value for 'SERVER.PORT'"):
        Config(config_file)


def test_invalid_port_range(temp_dir):
    """Test validation with port out of valid range"""
    config_file = os.path.join(temp_dir.name, "invalid_port.conf")
    mock_bin_dir = os.path.join(temp_dir.name, "mock_bin")
    os.makedirs(mock_bin_dir)
    open(f"{mock_bin_dir}/data.txt", 'w').close()
    config_content = f"""
[SERVER]
PORT = 70000
USE_SSL = false
WORKERS = 4
DEBUG = true

[SEARCH]
LINUX_PATH = {mock_bin_dir}/data.txt
ALGORITHM = simple
REREAD_ON_QUERY = false
CASE_SENSITIVE = true

[LOGGING]
LEVEL = INFO
"""
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    with pytest.raises(ConfigValidationError, match="Port must be between 1 and 65535"):
        Config(config_file)


def test_invalid_worker_count(temp_dir):
    """Test validation with invalid worker count"""
    config_file = os.path.join(temp_dir.name, "invalid_workers.conf")
    mock_bin_dir = os.path.join(temp_dir.name, "mock_bin")
    os.makedirs(mock_bin_dir)
    open(f"{mock_bin_dir}/data.txt", 'w').close()
    config_content = f"""
[SERVER]
PORT = 8080
USE_SSL = false
WORKERS = 0
DEBUG = true

[SEARCH]
LINUX_PATH = {mock_bin_dir}/data.txt
ALGORITHM = simple
REREAD_ON_QUERY = false
CASE_SENSITIVE = true

[LOGGING]
LEVEL = INFO
"""
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    with pytest.raises(ConfigValidationError, match="Workers must be at least 1"):
        Config(config_file)


def test_nonexistent_linux_path(temp_dir):
    """Test validation when linux_path doesn't exist"""
    config_file = os.path.join(temp_dir.name, "bad_path.conf")
    
    config_content = """
[SERVER]
PORT = 8080
USE_SSL = false
WORKERS = 4
DEBUG = true

[SEARCH]
LINUX_PATH = /nonexistent/path
ALGORITHM = simple
REREAD_ON_QUERY = false
CASE_SENSITIVE = true

[LOGGING]
LEVEL = INFO
"""
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    with pytest.raises(ConfigValidationError, match="Search path does not exist"):
        Config(config_file)


def test_invalid_search_algorithm(temp_dir):
    """Test validation with invalid search algorithm"""
    config_file = os.path.join(temp_dir.name, "invalid_algorithm.conf")
    mock_bin_dir = os.path.join(temp_dir.name, "mock_bin")
    os.makedirs(mock_bin_dir)
    open(f"{mock_bin_dir}/data.txt", 'w').close()
        
    config_content = f"""
[SERVER]
PORT = 8080
USE_SSL = false
WORKERS = 4
DEBUG = true

[SEARCH]
LINUX_PATH = {mock_bin_dir}/data.txt
ALGORITHM = invalid_algorithm
REREAD_ON_QUERY = false
CASE_SENSITIVE = true

[LOGGING]
LEVEL = INFO
"""
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    with pytest.raises(ConfigValidationError, match="Invalid search algorithm"):
        Config(config_file)

def test_ssl_enabled_missing_cert(temp_dir):
    """Test SSL validation when cert is missing"""
    config_file = os.path.join(temp_dir.name, "ssl_missing_cert.conf")
    mock_bin_dir = os.path.join(temp_dir.name, "mock_bin")
    os.makedirs(mock_bin_dir)
    open(f"{mock_bin_dir}/data.txt", 'w').close()
    config_content = f"""
[SERVER]
PORT = 8080
USE_SSL = true
SSL_CERT = 
SSL_KEY = /some/key.pem
WORKERS = 4
DEBUG = true

[SEARCH]
LINUX_PATH = {mock_bin_dir}/data.txt
ALGORITHM = simple
REREAD_ON_QUERY = false
CASE_SENSITIVE = true

[LOGGING]
LEVEL = INFO
"""
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    with pytest.raises(ConfigValidationError, match="Required configuration 'SERVER.SSL_CERT' is empty"):
        Config(config_file)


def test_ssl_cert_file_not_found(temp_dir):
    """Test SSL validation when cert file doesn't exist"""
    config_file = os.path.join(temp_dir.name, "ssl_bad_cert.conf")
    mock_bin_dir = os.path.join(temp_dir.name, "mock_bin")
    os.makedirs(mock_bin_dir)
    open(f"{mock_bin_dir}/data.txt", 'w').close()
    config_content = f"""
[SERVER]
PORT = 8080
USE_SSL = true
SSL_CERT = /nonexistent/cert.pem
SSL_KEY = /nonexistent/key.pem
WORKERS = 4
DEBUG = true

[SEARCH]
LINUX_PATH = {mock_bin_dir}/data.txt
ALGORITHM = simple
REREAD_ON_QUERY = false
CASE_SENSITIVE = true

[LOGGING]
LEVEL = INFO
"""
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    with pytest.raises(ConfigValidationError, match="SSL certificate file not found"):
        Config(config_file)


def test_invalid_log_level(temp_dir):
    """Test validation with invalid log level"""
    config_file = os.path.join(temp_dir.name, "invalid_log_level.conf")
    mock_bin_dir = os.path.join(temp_dir.name, "mock_bin")
    os.makedirs(mock_bin_dir)
    open(f"{mock_bin_dir}/data.txt", 'w').close()
    config_content = f"""
[SERVER]
PORT = 8080
USE_SSL = false
WORKERS = 4
DEBUG = true

[SEARCH]
LINUX_PATH = {mock_bin_dir}/data.txt
ALGORITHM = simple
REREAD_ON_QUERY = false
CASE_SENSITIVE = true

[LOGGING]
LEVEL = INVALID_LEVEL
"""
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    with pytest.raises(ConfigValidationError, match="Invalid log level 'INVALID_LEVEL'"):
        Config(config_file)


def test_logger_initialization(valid_config_file):
    """Test logger initialization"""
    config = Config(valid_config_file)
    
    assert config.logger is not None
    assert config.logger.name == "SearchServer"
    assert config.logger.level == logging.INFO
    assert len(config.logger.handlers) >= 1  # At least console handler


def test_logger_file_creation_failure(temp_dir):
    """Test logger initialization when file creation fails"""
    config_file = os.path.join(temp_dir.name, "log_fail.conf")
    mock_bin_dir = os.path.join(temp_dir.name, "mock_bin")
    os.makedirs(mock_bin_dir)
    
    open(f"{mock_bin_dir}/data.txt", 'w').close()
    config_content = f"""
[SERVER]
PORT = 8080
USE_SSL = false
WORKERS = 4
DEBUG = true

[SEARCH]
LINUX_PATH = {mock_bin_dir}/data.txt
ALGORITHM = simple
REREAD_ON_QUERY = false
CASE_SENSITIVE = true

[LOGGING]
LEVEL = INFO
FILE = /nonexistent/deeply/nested/path/test.log
"""
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    with pytest.raises(ConfigError, match="Log file parent directory does not exist: '/nonexistent/deeply/nested'"):
        Config(config_file)


def test_get_method(valid_config_file):
    """Test the get method for config values"""
    config = Config(valid_config_file)
    
    assert config.get('SEARCH', 'ALGORITHM') == 'simple'
    assert config.get('SERVER', 'NONEXISTENT') is None
    
    with pytest.raises(ConfigError, match="Configuration section 'NONEXISTENT' not found"):
        config.get('NONEXISTENT', 'KEY')


def test_save_method(valid_config_file, temp_dir):
    """Test saving config to file"""
    config = Config(valid_config_file)
    new_file = os.path.join(temp_dir.name, "new_config.conf")
    
    config.save(new_file)
    
    assert os.path.exists(new_file)
    
    # Verify the saved config can be loaded
    new_config = Config(new_file)
    assert new_config.host == config.host
    assert new_config.port == config.port


def test_save_permission_denied(valid_config_file, temp_dir):
    """Test save method when permission is denied"""
    config = Config(valid_config_file)
    
    # Create a directory without write permissions
    readonly_dir = os.path.join(temp_dir.name, "readonly")
    os.makedirs(readonly_dir)
    os.chmod(readonly_dir, 0o444)
    
    readonly_file = os.path.join(readonly_dir, "config.conf")
    
    try:
        with pytest.raises(ConfigError, match=f"Directory '{readonly_dir}' is not writable"):
            config.save(readonly_file)
    finally:
        # Restore permissions for cleanup
        os.chmod(readonly_dir, 0o755)


def test_remove_option(valid_config_file, temp_dir):
    """Test removing a configuration option"""
    config = Config(valid_config_file)
    
    # Verify option exists
    assert config.get('SERVER', 'DEBUG') is not None
    
    # Remove option
    config.remove_option('SERVER', 'DEBUG')
    
    # Verify option is removed
    assert config.get('SERVER', 'DEBUG') is None


def test_remove_option_nonexistent_section(valid_config_file):
    """Test removing option from nonexistent section"""
    config = Config(valid_config_file)
    
    with pytest.raises(ConfigError, match="Configuration section 'NONEXISTENT' not found"):
        config.remove_option('NONEXISTENT', 'KEY')


def test_remove_option_nonexistent_key(valid_config_file):
    """Test removing nonexistent option"""
    config = Config(valid_config_file)
    
    with pytest.raises(ConfigError, match="Key 'NONEXISTENT' not found in section 'SERVER'"):
        config.remove_option('SERVER', 'NONEXISTENT')


def test_reload_config(valid_config_file, temp_dir):
    """Test reloading configuration"""
    config = Config(valid_config_file)
    original_host = config.host
    
    # Modify the config file
    modified_content = config.config
    modified_content['SERVER']['HOST'] = 'modified_host'
    with open(valid_config_file, 'w') as f:
        modified_content.write(f)
    
    # Reload should pick up the change
    config.reload()
    assert config.host == 'localhost'


def test_reload_config_failure(valid_config_file):
    """Test reload when new config is invalid"""
    config = Config(valid_config_file)
    original_host = config.host
    
    # Corrupt the config file
    with open(valid_config_file, 'w') as f:
        f.write("INVALID CONFIG CONTENT")
    
    # Reload should fail and preserve original state
    with pytest.raises(ConfigError, match="Failed to reload configuration"):
        config.reload()
    
    # Original config should be preserved
    assert config.host == original_host


def test_str_representation(valid_config_file):
    """Test string representation of config"""
    config = Config(valid_config_file)
    config_str = str(config)
    
    assert "Config(" in config_str
    assert "host='localhost'" in config_str
    assert "port=8080" in config_str
    assert "workers=4" in config_str
    assert "debug=True" in config_str


def test_boolean_validation_edge_cases(temp_dir):
    """Test boolean validation with various input formats"""
    config_file = os.path.join(temp_dir.name, "bool_test.conf")
    mock_bin_dir = os.path.join(temp_dir.name, "mock_bin")
    os.makedirs(mock_bin_dir)
    
    open(f"{mock_bin_dir}/data.txt", 'w').close()
    config_content = f"""
[SERVER]
PORT = 8080
USE_SSL = maybe
WORKERS = 4
DEBUG = true

[SEARCH]
LINUX_PATH = {mock_bin_dir}/data.txt
ALGORITHM = simple
REREAD_ON_QUERY = false
CASE_SENSITIVE = true

[LOGGING]
LEVEL = INFO
"""
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    with pytest.raises(ConfigValidationError, match="Invalid boolean value for 'SERVER.USE_SSL'"):
        Config(config_file)