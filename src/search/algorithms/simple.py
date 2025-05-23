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
    SimpleSearch Algorithm Implementation for String Search

    This class implements a basic line-by-line search algorithm that extends the
    SearchAlgorithm base class. It performs exact matching between lines in the file
    and the provided query string, using an efficient buffered reading approach.

    The search reads the file in chunks of a specified buffer size, processes complete
    lines from the buffer, and carries over any incomplete line to the next iteration.
    Each complete line is compared directly to the query after encoding to bytes.

    Args:
        file_path (str): Path to the file to search in
        reread_on_query (bool, optional): Whether to reread the file for each query. Defaults to False.

    Attributes:
        stats (Dict): Dictionary tracking search performance statistics including comparison count
                    and total time taken
        _file_size (int): Size of the target file in bytes
        _buffer_size (int): Buffer size for file reading, capped at 8192 bytes or file size
        reread_on_query (bool): Flag indicating whether to reread the file on each query

    Methods:
        _read_file(): Placeholder method (not implemented in current version)
        search(query): Searches for an exact match of the provided query string in the file
        get_stats(): Returns statistics about the last search operation

    Implementation Details:
        The search method uses a buffered reading approach where:
        1. The file is read in chunks of _buffer_size bytes
        2. Lines are extracted from the buffer by splitting on newline characters
        3. The last (potentially incomplete) line is carried over to the next buffer
        4. Each complete line is compared to the query
        5. Search returns True immediately upon finding a match

    Example:
        >>> ss = SimpleSearch('/path/to/file.txt')
        >>> ss.search('pattern')
        True
        >>> ss.get_stats()
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
        return self.stats