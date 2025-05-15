import pytest
import tempfile
import os
from src.config.config import Config

@pytest.fixture
def temp_config_file():
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("""server.host=localhost
server.port=8443
server.workers=4
server.debug=false

ssl.enabled=true
ssl.cert_file=certs/server.crt
ssl.key_file=certs/server.key

search.algorithm=inmemory
search.data_file=data/search_data.txt
search.case_sensitive=false
search.max_results=100

logging.level=INFO
logging.file=logs/server.log""")
        return f.name

def test_config_loading(temp_config_file):
    config = Config(temp_config_file)
    assert config.get('server', 'host') == 'localhost'
    assert config.get('server', 'port') == '8443'
    assert config.get('search', 'algorithm') == 'inmemory'
    assert config.get('ssl', 'enabled') == 'true'
    
    # Test attribute mapping
    assert config.host == 'localhost'
    assert config.port == 8443
    assert config.workers == 4
    assert config.debug is False
    assert config.use_ssl is True
    assert config.linux_path == 'data/search_data.txt'

def test_config_missing_file():
    with pytest.raises(FileNotFoundError):
        Config('nonexistent.conf')

def test_config_invalid_section():
    with pytest.raises(KeyError):
        config = Config(temp_config_file)
        config.get('invalid_section', 'key')

def test_config_invalid_key():
    with pytest.raises(KeyError):
        config = Config(temp_config_file)
        config.get('server', 'invalid_key') 