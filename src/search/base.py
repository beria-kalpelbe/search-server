from abc import ABC, abstractmethod
from typing import Iterator, Optional, List

class SearchAlgorithm(ABC):
    """
    Abstract base class defining the interface for search algorithm implementations.

    This class establishes the core contract that all search algorithms must follow,
    providing a consistent API for file searching operations. It handles basic file
    management and defines the required interface methods.

    Args:
        file_path (str): Path to the file to be searched.

    Attributes:
        file_path (str): Path to the target file.
        _last_modified (float): Timestamp of last file modification.
        _lines (List[str]): Cached file content, if applicable.
        reread_on_query (bool): Whether to reread file content on each query.

    Note:
        Concrete implementations must override the abstract methods and may add
        additional functionality specific to their search strategy.
    """
    def __init__(self, file_path: str, case_sensitive: bool = True) -> None:
        self.file_path = file_path
        self._last_modified: float = 0.0
        self._lines = []
        self.case_sensitive = case_sensitive
        self.reread_on_query = False
    
    @abstractmethod
    def _read_file(self) -> None:
        """
        Reads and processes the target file.

        This method should be implemented by concrete classes to handle
        file reading according to their specific needs.
        """
        pass
    
    @abstractmethod
    def search(self, query: str) -> bool:
        """
        Performs a search operation for the given query.

        Args:
            query (str): The string to search for.

        Returns:
            bool: True if the query was found, False otherwise.

        Note:
            Implementations should handle file rereading if reread_on_query is True.
        """
        if self.reread_on_query:
            self._read_file()
        pass
    
    @abstractmethod
    def get_stats(self) -> dict:
        """
        Retrieves search operation statistics.

        Returns:
            dict: A dictionary containing algorithm-specific performance metrics.
        """
        pass
    
    def _read_file(self) -> None:
        """
        Reads and caches file content with optimized buffering.

        This implementation provides efficient file reading with:
            - File modification checking to avoid unnecessary reloads
            - Large buffer sizes for improved I/O performance
            - UTF-8 decoding with error handling
            - Memory-efficient line storage

        Raises:
            FileNotFoundError: If the target file does not exist.
            RuntimeError: If file reading encounters an error.
        """
        import os
        
        try:
            current_mtime = os.path.getmtime(self.file_path)
            if self._lines and current_mtime <= self._last_modified:
                return
            self._last_modified = current_mtime
        except (FileNotFoundError, OSError):
            pass
                
        try:
            buffer_size = 8 * 1024 * 1024  # 8MB buffer for optimal I/O
            with open(self.file_path, 'rb', buffering=buffer_size) as file:
                if not self.case_sensitive:
                    self._lines = [line.rstrip().decode('utf-8', errors='replace').lower() 
                             for line in file]
                else:
                    self._lines = [line.rstrip().decode('utf-8', errors='replace') 
                             for line in file]
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {self.file_path}")
        except Exception as e:
            raise RuntimeError(f"Error reading file: {e}")