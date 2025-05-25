import os
import sys
import configparser
from typing import Any, Dict, Optional
import logging
from logging.handlers import RotatingFileHandler


class ConfigError(Exception):
    """Base exception for configuration-related errors."""
    pass


class ConfigValidationError(ConfigError):
    """Raised when configuration validation fails."""
    pass


class ConfigFileError(ConfigError):
    """Raised when there are issues with the configuration file."""
    pass


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

    VALID_LOG_LEVELS = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
    VALID_ALGORITHMS = {'simple', 'inmemory', 'binary', 'hash', 'regex', 'bloom', 'boyermoore', 'kmp', 'rabinkarp', 'grep'}

    def __init__(self, config_file: str = "src/config/server.conf") -> None:
        """Initializes the configuration from a file.

        Args:
            config_file: Path to the configuration INI file.

        Raises:
            ConfigFileError: If the config file does not exist or cannot be read.
            ConfigValidationError: If required settings are missing or invalid.
        """
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.logger: Optional[logging.Logger] = None

        try:
            self._load_config_file()
            self._parse_configuration()
            self._validate_config()
            self._initiate_logger()
        except (ConfigFileError, ConfigValidationError) as e:
            raise
        except Exception as e:
            raise ConfigError(f"Unexpected error during configuration initialization: {e}") from e

    def _load_config_file(self) -> None:
        """Loads and parses the configuration file.
        
        Raises:
            ConfigFileError: If file doesn't exist, can't be read, or has parsing errors.
        """
        if not os.path.exists(self.config_file):
            raise ConfigFileError(f"Configuration file '{self.config_file}' not found")

        if not os.access(self.config_file, os.R_OK):
            raise ConfigFileError(f"Configuration file '{self.config_file}' is not readable")

        try:
            self.config.read(self.config_file)
        except configparser.Error as e:
            raise ConfigFileError(f"Failed to parse configuration file '{self.config_file}': {e}") from e
        except Exception as e:
            raise ConfigFileError(f"Unexpected error reading configuration file '{self.config_file}': {e}") from e

        # Validate that required sections exist
        required_sections = ['SERVER', 'SEARCH', 'LOGGING']
        missing_sections = [section for section in required_sections if section not in self.config]
        if missing_sections:
            raise ConfigFileError(f"Missing required sections in config file: {missing_sections}")

    def _get_required_int(self, section: str, key: str) -> int:
        """Retrieves a required integer value from config.
        
        Args:
            section: Configuration section name.
            key: Key within the section.
            
        Returns:
            Integer value.
            
        Raises:
            ConfigValidationError: If value is missing or cannot be converted to int.
        """
        if section not in self.config or key not in self.config[section]:
            raise ConfigValidationError(f"Required configuration '{section}.{key}' not found")
        
        value = self.config[section].get(key)
        if not value or not value.strip():
            raise ConfigValidationError(f"Required configuration '{section}.{key}' is empty")
        
        try:
            return self.config[section].getint(key)
        except ValueError as e:
            raise ConfigValidationError(f"Invalid integer value for '{section}.{key}': '{value}'") from e

    def _get_required_bool(self, section: str, key: str) -> bool:
        """Retrieves a required boolean value from config.
        
        Args:
            section: Configuration section name.
            key: Key within the section.
            
        Returns:
            Boolean value.
            
        Raises:
            ConfigValidationError: If value is missing or cannot be converted to bool.
        """
        if section not in self.config or key not in self.config[section]:
            raise ConfigValidationError(f"Required configuration '{section}.{key}' not found")
        
        value = self.config[section].get(key)
        if not value or not value.strip():
            raise ConfigValidationError(f"Required configuration '{section}.{key}' is empty")
        
        try:
            return self.config[section].getboolean(key)
        except ValueError as e:
            raise ConfigValidationError(f"Invalid boolean value for '{section}.{key}': '{value}'. Use true/false, yes/no, or 1/0") from e

    def _get_required_str(self, section: str, key: str) -> str:
        """Retrieves a required string value from config.
        
        Args:
            section: Configuration section name.
            key: Key within the section.
            
        Returns:
            String value.
            
        Raises:
            ConfigValidationError: If value is missing or empty.
        """
        if section not in self.config or key not in self.config[section]:
            raise ConfigValidationError(f"Required configuration '{section}.{key}' not found")
        
        value = self.config[section].get(key)
        if not value or not value.strip():
            raise ConfigValidationError(f"Required configuration '{section}.{key}' is empty")
        
        return value.strip()

    def _get_optional_str(self, section: str, key: str) -> Optional[str]:
        """Retrieves an optional string value from config.
        
        Args:
            section: Configuration section name.
            key: Key within the section.
            
        Returns:
            String value or None if not present or empty.
        """
        if section not in self.config or key not in self.config[section]:
            return None
        
        value = self.config[section].get(key)
        if not value or not value.strip():
            return None
        
        return value.strip()

    def _parse_configuration(self) -> None:
        """Parses all configuration values with strict validation."""
        # Server configuration - all required
        self.host = 'localhost'
        self.port = self._get_required_int("SERVER", "PORT")
        self.use_ssl = self._get_required_bool("SERVER", "USE_SSL")
        self.workers = self._get_required_int("SERVER", "WORKERS")
        self.debug = self._get_required_bool("SERVER", "DEBUG")
        
        # SSL configuration - required only if SSL is enabled
        if self.use_ssl:
            self.ssl_cert = self._get_required_str("SERVER", "SSL_CERT")
            self.ssl_key = self._get_required_str("SERVER", "SSL_KEY")
        else:
            self.ssl_cert = self._get_optional_str("SERVER", "SSL_CERT")
            self.ssl_key = self._get_optional_str("SERVER", "SSL_KEY")

        # Search configuration - all required
        self.linux_path = self._get_required_str("SEARCH", "LINUX_PATH")
        self.search_algorithm = self._get_required_str("SEARCH", "ALGORITHM")
        self.reread_on_query = self._get_required_bool("SEARCH", "REREAD_ON_QUERY")
        self.case_sensitive = self._get_required_bool("SEARCH", "CASE_SENSITIVE")

        # Logging configuration
        self.log_level = self._get_required_str("LOGGING", "LEVEL")
        self.log_file = self._get_optional_str("LOGGING", "FILE")  # Optional

    def _create_log_file(self, log_path: str) -> None:
        """Creates a log file and its directory structure if needed.

        Args:
            log_path: Path to the log file.

        Raises:
            ConfigError: If log file or directory cannot be created.
        """
        try:
            directory = os.path.dirname(log_path)
            if directory:
                if not os.path.exists(directory):
                    os.makedirs(directory, mode=0o755)
                elif not os.access(directory, os.W_OK):
                    raise ConfigError(f"Log directory '{directory}' is not writable")
                
            if os.path.exists(log_path):
                if not os.access(log_path, os.W_OK):
                    raise ConfigError(f"Log file '{log_path}' is not writable")
            else:
                try:
                    with open(log_path, "x", encoding="utf-8") as f:
                        pass
                except FileExistsError:
                    pass
                except PermissionError:
                    raise ConfigError(f"Permission denied when creating log file '{log_path}'")
                    
        except OSError as e:
            raise ConfigError(f"Failed to create log file or directory for '{log_path}': {e}") from e

    def _validate_config(self) -> None:
        """Validates all configuration settings strictly.

        Raises:
            ConfigValidationError: If any settings are invalid.
        """
        if not (1 <= self.port <= 65535):
            raise ConfigValidationError(f"Port must be between 1 and 65535, got: {self.port}")

        if self.workers < 1:
            raise ConfigValidationError(f"Workers must be at least 1, got: {self.workers}")
        if self.workers > 10_000:
            raise ConfigValidationError(f"Workers should not exceed 10 000, got: {self.workers}")

        if not os.path.exists(self.linux_path):
            raise ConfigValidationError(f"Search path does not exist: '{self.linux_path}'")
        if not os.access(self.linux_path, os.R_OK):
            raise ConfigValidationError(f"Search path is not readable: '{self.linux_path}'")
        if not os.path.isfile(self.linux_path):
            raise ConfigValidationError(f"Search path is not a file: '{self.linux_path}'")

        # Validate search algorithm
        if self.search_algorithm not in self.VALID_ALGORITHMS:
            raise ConfigValidationError(
                f"Invalid search algorithm '{self.search_algorithm}'. "
                f"Valid options: {', '.join(sorted(self.VALID_ALGORITHMS))}"
            )

        # Validate SSL configuration when enabled
        if self.use_ssl:
            if not self.ssl_cert:
                raise ConfigValidationError("SSL is enabled but SSL_CERT is missing or empty")
            if not self.ssl_key:
                raise ConfigValidationError("SSL is enabled but SSL_KEY is missing or empty")
            
            if not os.path.exists(self.ssl_cert):
                raise ConfigValidationError(f"SSL certificate file not found: '{self.ssl_cert}'")
            if not os.access(self.ssl_cert, os.R_OK):
                raise ConfigValidationError(f"SSL certificate file is not readable: '{self.ssl_cert}'")
            if not os.path.isfile(self.ssl_cert):
                raise ConfigValidationError(f"SSL certificate path is not a file: '{self.ssl_cert}'")
                
            if not os.path.exists(self.ssl_key):
                raise ConfigValidationError(f"SSL key file not found: '{self.ssl_key}'")
            if not os.access(self.ssl_key, os.R_OK):
                raise ConfigValidationError(f"SSL key file is not readable: '{self.ssl_key}'")
            if not os.path.isfile(self.ssl_key):
                raise ConfigValidationError(f"SSL key path is not a file: '{self.ssl_key}'")

        # Validate log level
        if self.log_level.upper() not in self.VALID_LOG_LEVELS:
            raise ConfigValidationError(
                f"Invalid log level '{self.log_level}'. "
                f"Valid options: {', '.join(sorted(self.VALID_LOG_LEVELS))}"
            )

        # Validate log file if specified
        if self.log_file:
            log_dir = os.path.dirname(self.log_file)
            if log_dir and not os.path.exists(log_dir):
                parent_dir = os.path.dirname(log_dir)
                if parent_dir and not os.path.exists(parent_dir):
                    raise ConfigValidationError(f"Log file parent directory does not exist: '{parent_dir}'")

    def _initiate_logger(self) -> None:
        """Initializes the logger with console and file handlers.

        Sets up:
            - Logging format.
            - Console handler (stderr).
            - File handler (if `log_file` is specified).
            - Log rotation (10MB per file, max 3 backups).
            
        Raises:
            ConfigError: If logger setup fails.
        """
        log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        formatter = logging.Formatter(log_format)

        try:
            log_level = getattr(logging, self.log_level.upper())
        except AttributeError:
            raise ConfigError(f"Invalid log level: {self.log_level}")

        self.logger = logging.getLogger("SearchServer")
        self.logger.setLevel(log_level)

        # Clear existing handlers to avoid duplicates
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # Console handler setup 
        try:
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(log_level)
            self.logger.addHandler(console_handler)
        except Exception as e:
            raise ConfigError(f"Failed to initialize console logging: {e}") from e

        # File handler setup - optional but must work if specified
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
                raise ConfigError(f"Failed to initialize file logging for '{self.log_file}': {e}") from e

    def get(self, section: str, key: str) -> Any:
        """Retrieves a raw value from the configuration.

        Args:
            section: INI section name.
            key: Key within the section.

        Returns:
            The value as a string (or None if not found).
            
        Raises:
            ConfigError: If section doesn't exist.
        """
        if section not in self.config:
            raise ConfigError(f"Configuration section '{section}' not found")
        return self.config[section].get(key)

    def __str__(self) -> str:
        """Returns a string representation of key settings."""
        return (
            f"Config(host='{self.host}', port={self.port}, "
            f"workers={self.workers}, debug={self.debug}, "
            f"use_ssl={self.use_ssl}, linux_path='{self.linux_path}', "
            f"algorithm='{self.search_algorithm}', "
            f"reread_on_query={self.reread_on_query})"
        )

    def save(self, config_file: Optional[str] = None) -> None:
        """Saves the current configuration to a file.

        Args:
            config_file: Path to the output INI file. If None, uses original config file.
            
        Raises:
            ConfigError: If file cannot be written.
        """
        target_file = config_file or self.config_file
        
        try:
            # Test write permissions first
            directory = os.path.dirname(target_file)
            if directory:
                if not os.path.exists(directory):
                    os.makedirs(directory, mode=0o755)
                elif not os.access(directory, os.W_OK):
                    raise ConfigError(f"Directory '{directory}' is not writable")
            
            # Create backup if file exists
            if os.path.exists(target_file):
                if not os.access(target_file, os.W_OK):
                    raise ConfigError(f"Config file '{target_file}' is not writable")
                
                backup_file = f"{target_file}.backup"
                try:
                    import shutil
                    shutil.copy2(target_file, backup_file)
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Failed to create backup of config file: {e}")
            
            with open(target_file, "w", encoding="utf-8") as f:
                self.config.write(f)
                
            if self.logger:
                self.logger.info(f"Configuration saved to: {target_file}")
                
        except PermissionError as e:
            raise ConfigError(f"Permission denied when writing to config file '{target_file}': {e}") from e
        except OSError as e:
            raise ConfigError(f"Failed to save configuration file '{target_file}': {e}") from e
    
    def remove_option(self, section: str, key: str) -> None:
        """Removes a key from the configuration.

        Args:
            section: INI section name.
            key: Key within the section.
            
        Raises:
            ConfigError: If section or key doesn't exist, or file cannot be saved.
        """
        if section not in self.config:
            raise ConfigError(f"Configuration section '{section}' not found")
            
        if key not in self.config[section]:
            raise ConfigError(f"Key '{key}' not found in section '{section}'")
        
        try:
            del self.config[section][key]
            self.save()
            if self.logger:
                self.logger.info(f"Removed configuration option: {section}.{key}")
        except Exception as e:
            raise ConfigError(f"Failed to remove configuration option '{section}.{key}': {e}") from e

    def reload(self) -> None:
        """Reloads configuration from the original file.
        
        Raises:
            ConfigFileError: If file cannot be reloaded.
            ConfigValidationError: If reloaded config is invalid.
        """
        try:
            old_config = self.config
            old_logger = self.logger
            
            # Reinitialize
            self.__init__(self.config_file)
            
            if self.logger:
                self.logger.info("Configuration reloaded successfully")
                
        except Exception as e:
            # Restore previous state if reload fails
            self.config = old_config
            self.logger = old_logger
            raise ConfigError(f"Failed to reload configuration: {e}") from e