import os
import sys
import configparser
from typing import Any, Dict, Optional
import logging
from logging.handlers import RotatingFileHandler


class Config:
    """Manages server configuration and logging setup.

    Reads settings from an INI file, validates them, and initializes a logger
    with both console and file handlers (if specified).

    Attributes:
        host (str): Server host address.
        port (int): Server port number.
        use_ssl (bool): Whether SSL is enabled.
        ssl_cert (str): Path to SSL certificate.
        ssl_key (str): Path to SSL private key.
        workers (int): Number of worker processes.
        debug (bool): Debug mode flag.
        linux_path (str): Filesystem path for search operations.
        search_algorithm (str): Algorithm used for search.
        reread_on_query (bool): Whether to re-read files on each query.
        case_sensitive (bool): Whether search is case-sensitive.
        log_level (str): Logging level (e.g., "INFO", "DEBUG").
        log_file (Optional[str]): Path to log file (if specified).
        logger (Optional[logging.Logger]): Configured logger instance.
    """

    def __init__(self, config_file: str = "src/config/server.conf") -> None:
        """Initializes the configuration from a file.

        Args:
            config_file: Path to the configuration INI file.

        Raises:
            FileNotFoundError: If the config file does not exist.
            ValueError: If required settings are missing or invalid.
        """
        self.config = configparser.ConfigParser()

        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file {config_file} not found")

        self.config.read(config_file)

        server_config = self.config["SERVER"]
        self.host: str = server_config.get("HOST", "localhost")
        self.port: int = server_config.getint("PORT", 8080)
        self.use_ssl: bool = server_config.getboolean("USE_SSL", False)
        self.ssl_cert: Optional[str] = server_config.get("SSL_CERT")
        self.ssl_key: Optional[str] = server_config.get("SSL_KEY")
        self.workers: int = server_config.getint("WORKERS", 4)
        self.debug: bool = server_config.getboolean("DEBUG", False)

        search_config = self.config["SEARCH"]
        self.linux_path: str = search_config.get("LINUX_PATH")
        self.search_algorithm: str = search_config.get("ALGORITHM", "simple")
        self.reread_on_query: bool = search_config.getboolean("REREAD_ON_QUERY")
        self.case_sensitive: bool = search_config.getboolean("CASE_SENSITIVE")

        logging_config = self.config["LOGGING"]
        self.log_level: str = logging_config.get("level", "INFO")
        self.log_file: Optional[str] = logging_config.get("file")
        self.logger: Optional[logging.Logger] = None

        self._validate_config()
        self._initiate_logger()

    def _create_log_file(self, log_path: str) -> None:
        """Creates a log file and its directory structure if needed.

        Args:
            log_path: Path to the log file.

        Note:
            Silently skips if the file already exists.
        """
        directory = os.path.dirname(log_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        try:
            with open(log_path, "x", encoding="utf-8") as f:
                pass
        except FileExistsError:
            pass

    def _validate_config(self) -> None:
        """Validates critical configuration settings.

        Raises:
            ValueError: If required settings are missing or invalid.
        """
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
        """Initializes the logger with console and file handlers.

        Sets up:
            - Logging format.
            - Console handler (stderr).
            - File handler (if `log_file` is specified).
            - Log rotation (10MB per file, max 3 backups).
        """
        log_format = "%(asctime)s [%(levelname)s] %(message)s"
        formatter = logging.Formatter(log_format)

        log_level = getattr(logging, self.log_level.upper(), logging.INFO)

        self.logger = logging.getLogger("SearchServer")
        self.logger.setLevel(log_level)

        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        self.logger.addHandler(console_handler)

        if self.log_file:
            try:
                self._create_log_file(self.log_file)
                file_handler = RotatingFileHandler(
                    self.log_file,
                    maxBytes=10 * 1024 * 1024,  # 10MB
                    backupCount=3,
                    encoding="utf-8",
                )
                file_handler.setFormatter(formatter)
                file_handler.setLevel(log_level)
                self.logger.addHandler(file_handler)
            except Exception as e:
                self.logger.error("Failed to initialize file logging: %s", str(e))
                self.logger.warning("Continuing with console logging only")

    def get(self, section: str, key: str) -> Any:
        """Retrieves a raw value from the configuration.

        Args:
            section: INI section name.
            key: Key within the section.

        Returns:
            The value as a string (or None if not found).
        """
        return self.config[section].get(key)

    def __str__(self) -> str:
        """Returns a string representation of key settings."""
        return (
            f"Config(host='{self.host}', port={self.port}, "
            f"workers={self.workers}, debug={self.debug}, "
            f"use_ssl={self.use_ssl}, linux_path='{self.linux_path}', "
            f"reread_on_query={self.reread_on_query})"
        )

    def save(self, config_file: str) -> None:
        """Saves the current configuration to a file.

        Args:
            config_file: Path to the output INI file.
        """
        with open(config_file, "w", encoding="utf-8") as f:
            self.config.write(f)
    
    def remove_option(self, section: str, key: str) -> None:
        """Removes a key from the configuration.

        Args:
            section: INI section name.
            key: Key within the section.
        """
        if section in self.config and key in self.config[section]:
            del self.config[section][key]
            self.save(self.config_file)
        else:
            raise KeyError(f"Key '{key}' not found in section '{section}'")