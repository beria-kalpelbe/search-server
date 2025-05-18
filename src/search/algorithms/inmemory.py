import re
import time
import os
from typing import Iterator, Dict, List, Optional, Set
import mmh3
from pybloom_live import BloomFilter
import datrie
from src.search.base import SearchAlgorithm

class InMemorySearch(SearchAlgorithm):    
    def __init__(self, file_path: str, reread_on_query: bool = False):
        super().__init__(file_path)
        self.stats = {"load_time": 0, "search_time": 0}
        self._lines: Set[str] = set()
        self.reread_on_query = reread_on_query
        if not self.reread_on_query:
            self._read_file()
    
    def _read_file(self) -> None:
        start_time = time.time()
        with open(self.file_path, 'rb') as f:
            self._lines = {line.rstrip().decode('utf-8') for line in f}
        self.stats["load_time"] = time.time() - start_time
    
    def search(self, query: str) -> bool:
        start_time = time.time()
        super().search(query)
        if self.reread_on_query:
            self._read_file()
        self.stats["search_time"] = time.time() - start_time
        return query in self._lines
    
    def get_stats(self) -> dict:
        return self.stats