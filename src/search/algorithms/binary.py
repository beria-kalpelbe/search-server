import re
import time
import os
from typing import Iterator, Dict, List, Optional, Set
import mmh3
from pybloom_live import BloomFilter
import datrie
from src.search.base import SearchAlgorithm

class BinarySearch(SearchAlgorithm):    
    def __init__(self, file_path: str, reread_on_query: bool = False):
        super().__init__(file_path)
        self.stats = {"comparisons": 0, "time_taken": 0}
        self._sorted_lines: List[str] = []
        self.reread_on_query = reread_on_query
        if not self.reread_on_query:
            self._read_file()
    
    def _read_file(self) -> None:
        with open(self.file_path, 'rb') as f:
            self._sorted_lines = sorted(line.rstrip().decode('utf-8') for line in f)
    
    def search(self, query: str) -> bool:
        start_time = time.time()
        super().search(query)
        if self.reread_on_query:
            self._read_file()
        self.stats["comparisons"] = 0
        result = False
        left, right = 0, len(self._sorted_lines) - 1
        while left <= right:
            mid = (left + right) >> 1  # Faster than division
            self.stats["comparisons"] += 1
            
            if self._sorted_lines[mid] == query:
                result = True
                break
            elif self._sorted_lines[mid] < query:
                left = mid + 1
            else:
                right = mid - 1
        self.stats["time_taken"] = time.time() - start_time
        return result
    
    def get_stats(self) -> dict:
        return self.stats