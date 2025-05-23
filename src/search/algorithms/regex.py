import re
import time
import os
from typing import Iterator, Dict, List, Optional, Set
import mmh3
from pybloom_live import BloomFilter
import datrie
from src.search.base import SearchAlgorithm

class RegexSearch(SearchAlgorithm):
    """
    RegexSearch Algorithm Implementation for String Search

    This class implements a regular expression-based search algorithm that extends
    the SearchAlgorithm base class. Despite its name, the current implementation 
    performs exact byte-level matching rather than regex pattern matching, comparing
    each line in the file with the query string.

    The search is performed on a line-by-line basis, with each line compared directly
    to the query after encoding to bytes. The class can either cache the file content
    or reread it for each query based on configuration.

    Args:
        file_path (str): Path to the file to search in
        reread_on_query (bool, optional): Whether to reread the file for each query. Defaults to False.

    Attributes:
        stats (Dict): Dictionary tracking search performance statistics including compile time and search time
        _pattern (Optional[re.Pattern]): Placeholder for regex pattern (unused in current implementation)
        _file_size (int): Size of the target file in bytes
        _buffer_size (int): Buffer size for file reading, capped at 8192 bytes or file size
        reread_on_query (bool): Flag indicating whether to reread the file on each query
        _lines (List[bytes]): Lines of the file stored as byte strings for searching

    Methods:
        _read_file(): Reads the file and stores each line as bytes in the _lines attribute
        search(query): Searches for an exact match of the provided query string in the file
        get_stats(): Returns timing statistics about the last search operation

    Example:
        >>> rs = RegexSearch('/path/to/file.txt')
        >>> rs.search('pattern')
        True
        >>> rs.get_stats()
        {'compile_time': 0.0001, 'search_time': 0.0023}
    """
    def __init__(self, file_path: str, reread_on_query: bool = False, case_sensitive: bool = True) -> None:
        super().__init__(file_path)
        self.stats = {"compile_time": 0, "search_time": 0}
        self._pattern: Optional[re.Pattern] = None
        self._file_size = os.path.getsize(file_path)
        self._buffer_size = min(8192, self._file_size)
        self.reread_on_query = reread_on_query
        self.case_sensitive = case_sensitive
        if not self.reread_on_query:
            self._read_file()
    

    
    def search(self, query: str) -> bool:
        start_compile = time.time()
        super().search(query)
        if self.reread_on_query:
            self._read_file()
        self.stats["compile_time"] = time.time() - start_compile
        
        start_search = time.time()
        for line in self._lines:
            if not self.case_sensitive:
                line = line.lower()
                query = query.lower()
            if line == query:
                self.stats["search_time"] = time.time() - start_search
                return True
        
        self.stats["search_time"] = time.time() - start_search
        return False
    
    def get_stats(self) -> dict:
        return self.stats