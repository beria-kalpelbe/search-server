import re
import time
import os
from typing import Iterator, Dict, List, Optional, Set
import mmh3
from pybloom_live import BloomFilter
import datrie
from src.search.base import SearchAlgorithm

class SimpleSearch(SearchAlgorithm):    
    """
    A basic line-by-line search implementation optimized for sequential file scanning.

    This class provides a straightforward search algorithm that reads the file line by line,
    comparing each line directly with the query string. While simple in approach, it can be
    efficient for small files or when memory usage needs to be minimized.

    Args:
        file_path (str): Path to the file to search.
        reread_on_query (bool, optional): Whether to reread the file for each query.
            Defaults to False.

    Attributes:
        stats (Dict): Performance statistics including:
            - comparisons: Number of line comparisons performed
            - time_taken: Total search execution time in seconds
        _file_size (int): Size of the target file in bytes
        _buffer_size (int): Buffer size for file reading operations
        reread_on_query (bool): Flag controlling file rereading behavior

    Example:
        >>> searcher = SimpleSearch('data.txt')
        >>> found = searcher.search('example text')
        >>> print(searcher.get_stats())
        {'comparisons': 42, 'time_taken': 0.0015}
    """
    def __init__(self, file_path: str, reread_on_query: bool = False):
        super().__init__(file_path)
        self.stats = {"comparisons": 0, "time_taken": 0}
        self._file_size = os.path.getsize(file_path)
        self._buffer_size = min(8192, self._file_size)
        self.reread_on_query = reread_on_query
        if not self.reread_on_query:
            self._read_file()
    
    def search(self, query: str) -> Iterator[bool]:
        """
        Performs a line-by-line search for the query string.

        Args:
            query (str): The string to search for in the file.

        Returns:
            bool: True if the query is found, False otherwise.

        Note:
            The search is case-sensitive and matches complete lines only.
            Performance statistics are updated after each search operation.
        """
        start_time = time.time()
        if self.reread_on_query:
            self._read_file()
        self.stats["comparisons"] = 0
        query_bytes = query.encode('utf-8') + b'\n'

        for line in self._lines[:-1]:
            self.stats["comparisons"] += 1
            if line == query_bytes.rstrip():
                self.stats["time_taken"] = time.time() - start_time
                return True
        self.stats["time_taken"] = time.time() - start_time
        return False
    
    def get_stats(self) -> dict:
        """
        Retrieves the current search statistics.

        Returns:
            dict: A dictionary containing performance metrics:
                - comparisons: Number of line comparisons performed
                - time_taken: Total search execution time in seconds
        """
        return self.stats