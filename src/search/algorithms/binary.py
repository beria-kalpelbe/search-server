import re
import time
import os
from typing import Iterator, Dict, List, Optional, Set
import mmh3
from pybloom_live import BloomFilter
import datrie
from src.search.base import SearchAlgorithm

class BinarySearch(SearchAlgorithm):    
    def __init__(self, file_path: str):
        super().__init__(file_path)
        self.stats = {"comparisons": 0, "time_taken": 0}
        self._sorted_lines: List[str] = []
    
    def _read_file(self) -> None:
        with open(self.file_path, 'rb') as f:
            self._sorted_lines = sorted(line.rstrip().decode('utf-8') for line in f)
    
    def prepare(self) -> None:
        self._read_file()
    
    def search(self, query: str) -> Iterator[str]:
        super().search(query)
        start_time = time.time()
        self.stats["comparisons"] = 0
        
        left, right = 0, len(self._sorted_lines) - 1
        while left <= right:
            mid = (left + right) >> 1  # Faster than division
            self.stats["comparisons"] += 1
            
            if self._sorted_lines[mid] == query:
                yield query
                break
            elif self._sorted_lines[mid] < query:
                left = mid + 1
            else:
                right = mid - 1
        
        self.stats["time_taken"] = time.time() - start_time
    
    def get_stats(self) -> dict:
        return self.stats