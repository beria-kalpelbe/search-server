from abc import ABC, abstractmethod
from typing import Iterator, Optional, List

class SearchAlgorithm(ABC):
    """
    SearchAlgorithm Abstract Base Class

    This abstract base class defines the interface for text search algorithm implementations.
    It provides a common structure and API for different search algorithms to implement,
    ensuring consistency across various searching techniques.

    The class establishes three core required methods that all search implementations must provide:
    file reading, search functionality, and statistics reporting. It also manages basic shared
    attributes such as file path and caching strategy.

    Args:
        file_path (str): Path to the file to be searched

    Attributes:
        file_path (str): Path to the file that will be searched
        reread_on_query (bool): Flag indicating whether to reread the file on each query

    Abstract Methods:
        _read_file(): 
            Reads and processes the file specified in file_path.
            Implementation is required in concrete subclasses.
            
        search(query):
            Searches for the provided query string in the file.
            Implementation is required in concrete subclasses.
            Args:
                query (str): The string to search for in the file
            Returns:
                Iterator[str]: An iterator of results (implementation-specific)
            
        get_stats():
            Returns statistics about the last search operation.
            Implementation is required in concrete subclasses.
            Returns:
                dict: Dictionary containing algorithm-specific statistics

    Methods:
        cleanup():
            Releases the cached file content if it exists.
            This helps manage memory usage after searches are complete.
    """
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._last_modified: float = 0.0
        self._lines = []
        self.reread_on_query = False
    
    @abstractmethod
    def _read_file(self) -> None:
        pass
    
    @abstractmethod
    def search(self, query: str) -> Iterator[str]:
        if self.reread_on_query:
            self._read_file()
        pass
    
    @abstractmethod
    def get_stats(self) -> dict:
        pass
    
    
    def _read_file(self) -> None:
        """
        Read the file and load its content into memory.
        
        This method reads the file specified by `file_path`, decodes its lines,
        and stores them in the `_lines` set.
        """
        import os
        
        # Check if file has been modified since last read
        try:
            current_mtime = os.path.getmtime(self.file_path)
            if self._lines and current_mtime <= self._last_modified:
                # File hasn't changed, no need to reload
                return
            self._last_modified = current_mtime
        except (FileNotFoundError, OSError):
            # Will be handled in the file opening block
            pass
                
        try:
            # Use a buffer size that balances memory usage and performance
            buffer_size = 8 * 1024 * 1024  # 8MB buffer
            with open(self.file_path, 'rb', buffering=buffer_size) as file:
                # Use a list comprehension instead of a set comprehension for better speed
                # when dealing with a large number of lines
                self._lines = [line.rstrip().decode('utf-8', errors='replace') for line in file]
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {self.file_path}")
        except Exception as e:
            raise RuntimeError(f"Error reading file: {e}")
        
