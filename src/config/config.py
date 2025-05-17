import os
import sys
import configparser
from typing import Dict, Any, Optional
import logging

class Config:
    def __init__(self, config_file: str = "src/config/server.conf"):
        self.config = configparser.ConfigParser()
        
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file {config_file} not found")
            
        self.config.read(config_file)
        
        server_config = self.config['SERVER']
        search_config = self.config['SEARCH']
        logging_config = self.config['LOGGING']
        
        self.host = server_config.get('HOST')
        self.port = server_config.getint('PORT')
        self.use_ssl = server_config.getboolean('USE_SSL')
        self.ssl_cert = server_config.get('SSL_CERT')
        self.ssl_key = server_config.get('SSL_KEY')
        self.workers = server_config.getint('WORKERS')
        self.debug = server_config.getboolean('DEBUG')
        
        self.linux_path = search_config.get('LINUX_PATH')
        self.search_algorithm = search_config.get('ALGORITHM')
        self.reread_on_query = search_config.getboolean('REREAD_ON_QUERY')
        self.case_sensitive = search_config.getboolean('CASE_SENSITIVE')
        # self.max_results = search_config.getint('MAX_RESULTS')
        
        self.log_level = logging_config.get('level')
        self.log_file = logging_config.get('file')
        self.logger = None
        
        self._validate_config()
        self._initiate_logger()
    
    def _create_log_file(self, log_path):
        directory = os.path.dirname(log_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        try:
            with open(log_path, "x") as f:
                pass
        except FileExistsError:
            # print(f"Log file already exists: {log_path}")
            pass
    
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
    
    def _initiate_logger(self) -> None:
        """Initialize the logger to output to both console and file (if specified)."""
        # Set up log format
        log_format = "%(asctime)s [%(levelname)s] %(message)s"
        formatter = logging.Formatter(log_format)
        
        # Get the log level
        log_level = getattr(logging, self.log_level.upper(), logging.INFO)
        
        # Create a logger instance
        self.logger = logging.getLogger("SearchServer")
        self.logger.setLevel(log_level)
        
        # Clear any existing handlers to avoid duplicate logs
        if self.logger.hasHandlers():
            self.logger.handlers.clear()
        
        # Create console handler and add it to logger
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        self.logger.addHandler(console_handler)
        
        # If log file is specified, create file handler and add it to logger
        if self.log_file:
            try:
                # Create the log file and directory if needed
                self._create_log_file(self.log_file)
                
                # Create file handler for log file
                from logging.handlers import RotatingFileHandler
                file_handler = RotatingFileHandler(
                    self.log_file,
                    maxBytes=10*1024*1024,  # 10MB
                    backupCount=3
                )
                file_handler.setFormatter(formatter)
                file_handler.setLevel(log_level)
                self.logger.addHandler(file_handler)
                
                self.logger.info(f"Logging to file: {self.log_file}")
            except Exception as e:
                # Continue with console logging even if file logging fails
                self.logger.error(f"Failed to initialize file logging to {self.log_file}: {e}")
                self.logger.warning("Continuing with console logging only")
    
    def get(self, section: str, key: str) -> Any:
        return self.config[section][key]
    
    def __str__(self) -> str:
        return (
            f"Config(HOST='{self.host}', port={self.port}, "
            f"WORKERS={self.workers}, debug={self.debug}, "
            f"USE_SSL={self.use_ssl}, linux_path='{self.linux_path}', "
            f"REREAD_ON_QUERY={self.reread_on_query})"
        )

    def save(self, config_file: str) -> None:
        with open(config_file, 'w') as f:
            self.config.write(f) 