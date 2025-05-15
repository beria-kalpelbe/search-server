"""Base interface for search algorithms."""

from abc import ABC, abstractmethod
from typing import Iterator, Optional, List

class SearchAlgorithm(ABC):
    """Abstract base class for search algorithms."""
    
    def __init__(self, file_path: str):
        """Initialize the search algorithm.
        
        Args:
            file_path: Path to the file to search in
        """
        self.file_path = file_path
        self._cache = None
    
    @abstractmethod
    def prepare(self) -> None:
        """Prepare the algorithm (build index, cache, etc.)."""
        pass
    
    @abstractmethod
    def search(self, query: str) -> Iterator[str]:
        """Search for a query in the file.
        
        Args:
            query: The search query
            
        Returns:
            Iterator of matching lines
        """
        pass
    
    @abstractmethod
    def get_stats(self) -> dict:
        """Get algorithm statistics.
        
        Returns:
            Dictionary containing algorithm statistics
        """
        pass
    
    def cleanup(self) -> None:
        """Clean up any resources."""
        if hasattr(self, '_cache'):
            self._cache = None 