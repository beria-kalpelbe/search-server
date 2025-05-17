import re
import time
import os
from typing import Iterator, Dict, List, Optional, Set
import mmh3
from pybloom_live import BloomFilter
import datrie
from src.search.base import SearchAlgorithm

class BloomFilterSearch(SearchAlgorithm):
    def __init__(self, file_path: str, capacity: int = 1000000, error_rate: float = 0.001):
        super().__init__(file_path)
        self.stats = {"filter_build_time": 0, "search_time": 0}
        self._bloom = BloomFilter(capacity=capacity, error_rate=error_rate)
        self._lines: Set[str] = set()
    
    def _read_file(self) -> None:
        start_time = time.time()
        self._bloom = BloomFilter(capacity=1000000, error_rate=0.001)
        self._lines.clear()
        with open(self.file_path, 'rb') as f:
            for line in f:
                line_str = line.rstrip().decode('utf-8')
                self._bloom.add(line_str)
                self._lines.add(line_str)
        self.stats["filter_build_time"] = time.time() - start_time
    
    def prepare(self) -> None:
        self._read_file()
    
    def search(self, query: str) -> Iterator[str]:
        super().search(query)
        start_time = time.time()
        if query in self._bloom and query in self._lines:
            yield query
        self.stats["search_time"] = time.time() - start_time
    
    def get_stats(self) -> dict:
        return self.stats 