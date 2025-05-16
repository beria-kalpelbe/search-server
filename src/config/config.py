import os
import configparser
from typing import Dict, Any, Optional

class Config:
    def __init__(self, config_file: str = "src/config/server.conf"):
        self.config = configparser.ConfigParser()
        
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file {config_file} not found")
            
        self.config.read(config_file)
        
        server_config = self.config['Server']
        search_config = self.config['Search']
        logging_config = self.config['Logging']
        
        self.host = server_config.get('host')
        self.port = server_config.getint('port')
        self.use_ssl = server_config.getboolean('use_ssl')
        self.ssl_cert = server_config.get('ssl_cert')
        self.ssl_key = server_config.get('ssl_key')
        self.workers = server_config.getint('workers')
        self.debug = server_config.getboolean('debug')
        
        self.linux_path = search_config.get('linux_path')
        self.search_algorithm = search_config.get('algorithm')
        self.reread_on_query = search_config.getboolean('reread_on_query')
        self.case_sensitive = search_config.getboolean('case_sensitive')
        self.max_results = search_config.getint('max_results')
        
        self.log_level = logging_config.get('level')
        self.log_file = logging_config.get('file')
        
        self._validate_config()
    
    def _validate_config(self) -> None:
        if not self.linux_path:
            raise ValueError("Required 'search.linux_path' configuration not found")
        
        if self.use_ssl:
            if not self.ssl_cert or not self.ssl_key:
                raise ValueError("SSL is enabled but cert_file or key_file is missing")
            if not os.path.exists(self.ssl_cert):
                raise ValueError(f"SSL certificate file not found: {self.ssl_cert}")
            if not os.path.exists(self.ssl_key):
                raise ValueError(f"SSL key file not found: {self.ssl_key}")
    
    def get(self, section: str, key: str) -> Any:
        return self.config[section][key]
    
    def __str__(self) -> str:
        return (
            f"Config(host='{self.host}', port={self.port}, "
            f"workers={self.workers}, debug={self.debug}, "
            f"use_ssl={self.use_ssl}, linux_path='{self.linux_path}', "
            f"reread_on_query={self.reread_on_query})"
        )

    def save(self, config_file: str) -> None:
        with open(config_file, 'w') as f:
            self.config.write(f) 