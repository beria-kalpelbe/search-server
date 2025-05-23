import time
from typing import Set, Dict, Any
from src.search.base import SearchAlgorithm


class InMemorySearch(SearchAlgorithm):
    """
    In-Memory Search Algorithm.
    
    This class provides an implementation of a search algorithm that loads
    file content into memory for efficient membership testing.
    
    Attributes:
        file_path (str): Path to the file to be searched.
        reread_on_query (bool): Whether to reread the file for each query.
        stats (dict): Statistics about the search process.
        _lines (Set[str]): A set of lines read from the file.
        _last_modified (float): Timestamp of last file modification.
    """
    
    def __init__(self, file_path: str, reread_on_query: bool = False, case_sensitive: bool = True) -> None: 
        """
        Initialize the InMemorySearch instance.
        
        Args:
            file_path (str): Path to the file to be searched.
            reread_on_query (bool): Whether to reread the file for each query.
        """
        super().__init__(file_path)
        self.stats: Dict[str, float] = {"load_time": 0.0, "search_time": 0.0}
        self._lines: Set[str] = set()
        self.reread_on_query = reread_on_query
        self.case_sensitive = case_sensitive
        self._last_modified: float = 0.0
        
        # Load file on initialization if not rereading on each query
        if not self.reread_on_query:
            self._read_file()
    
    
    def search(self, query: str) -> bool:
        """
        Perform a search for the query string in memory.
        
        Args:
            query (str): The string to search for.
        
        Returns:
            bool: True if the query is found, False otherwise.
        """
        start_time = time.time()
        if not self.case_sensitive:
            query = query.lower()
            
        if self.reread_on_query:
            self._read_file()
        
        # Direct set membership test is already O(1) on average
        result = query in self._lines
        
        self.stats["search_time"] = time.time() - start_time
        return result
    
    def get_stats(self) -> Dict[str, float]:
        """
        Retrieve search statistics.
        
        Returns:
            dict: A dictionary containing search statistics.
        """
        return self.stats.copy()  # Return a copy to prevent external modification