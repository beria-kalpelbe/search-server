"""Configuration module for the search server."""

import os
from typing import Dict, Any, Optional

class Config:
    def __init__(self, config_file: str = "server.conf"):
        """Initialize configuration.
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        # Required settings with defaults
        self.linux_path: str = ""
        self.use_ssl: bool = False
        self.reread_on_query: bool = False
        self.host: str = "localhost"
        self.port: int = 8443
        self.workers: int = 4
        self.debug: bool = False
        self.search_algorithm: str = "inmemory"
        self.case_sensitive: bool = False
        self.max_results: int = 100
        self.log_level: str = "INFO"
        self.log_file: Optional[str] = None
        self.ssl_cert: Optional[str] = None
        self.ssl_key: Optional[str] = None
        
        # Store raw config values
        self._config_dict: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file."""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Configuration file {self.config_file} not found")
            
        with open(self.config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Store in config dict
                    section, *rest = key.split('.')
                    if not rest:
                        self._config_dict[section] = value
                    else:
                        if section not in self._config_dict:
                            self._config_dict[section] = {}
                        curr = self._config_dict[section]
                        *path, final = rest
                        for part in path:
                            if part not in curr:
                                curr[part] = {}
                            curr = curr[part]
                        curr[final] = value
        
        # Map config values to class attributes
        self._map_config_values()
    
    def _map_config_values(self) -> None:
        """Map configuration values to class attributes."""
        # Server settings
        server = self._config_dict.get('server', {})
        if isinstance(server, dict):
            self.host = server.get('host', self.host)
            self.port = int(server.get('port', self.port))
            self.workers = int(server.get('workers', self.workers))
            self.debug = self._parse_bool(server.get('debug', self.debug))
        
        # SSL settings
        ssl = self._config_dict.get('ssl', {})
        if isinstance(ssl, dict):
            self.use_ssl = self._parse_bool(ssl.get('enabled', self.use_ssl))
            self.ssl_cert = ssl.get('cert_file')
            self.ssl_key = ssl.get('key_file')
        
        # Search settings
        search = self._config_dict.get('search', {})
        if isinstance(search, dict):
            self.linux_path = search.get('data_file', self.linux_path)
            self.reread_on_query = self._parse_bool(search.get('reread_on_query', self.reread_on_query))
            self.search_algorithm = search.get('algorithm', self.search_algorithm)
            self.case_sensitive = self._parse_bool(search.get('case_sensitive', self.case_sensitive))
            self.max_results = int(search.get('max_results', self.max_results))
        
        # Logging settings
        logging = self._config_dict.get('logging', {})
        if isinstance(logging, dict):
            self.log_level = logging.get('level', self.log_level)
            self.log_file = logging.get('file', self.log_file)
        
        # Validate required settings
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate required configuration settings."""
        if not self.linux_path:
            raise ValueError("Required 'search.data_file' configuration not found")
        
        if self.use_ssl:
            if not self.ssl_cert or not self.ssl_key:
                raise ValueError("SSL is enabled but cert_file or key_file is missing")
            if not os.path.exists(self.ssl_cert):
                raise ValueError(f"SSL certificate file not found: {self.ssl_cert}")
            if not os.path.exists(self.ssl_key):
                raise ValueError(f"SSL key file not found: {self.ssl_key}")
    
    @staticmethod
    def _parse_bool(value: Any) -> bool:
        """Parse boolean configuration values."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'on')
        return bool(value)
    
    def get(self, section: str, key: Optional[str] = None) -> Any:
        """Get a configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key within section (optional)
            
        Returns:
            Configuration value
        """
        if key is None:
            return self._config_dict.get(section)
        section_dict = self._config_dict.get(section, {})
        if not isinstance(section_dict, dict):
            raise KeyError(f"Section {section} has no nested keys")
        if key not in section_dict:
            raise KeyError(f"Key {key} not found in section {section}")
        return section_dict[key]
    
    def __str__(self) -> str:
        """Return string representation of configuration."""
        return (
            f"Config(host='{self.host}', port={self.port}, "
            f"workers={self.workers}, debug={self.debug}, "
            f"use_ssl={self.use_ssl}, linux_path='{self.linux_path}', "
            f"reread_on_query={self.reread_on_query})"
        ) 