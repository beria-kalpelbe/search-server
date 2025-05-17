import re
import time
import os
from typing import Iterator, Dict, List, Optional, Set
import mmh3
from pybloom_live import BloomFilter
import datrie
from src.search.base import SearchAlgorithm

class HashSearch(SearchAlgorithm):
    
    def __init__(self, file_path: str):
        super().__init__(file_path)
        self.stats = {"hash_time": 0, "search_time": 0}
        self._hash_set: Set[str] = set()
    
    def _read_file(self) -> None:
        start_time = time.time()
        self._hash_set.clear()
        
        with open(self.file_path, 'rb') as f:
            for line in f:
                self._hash_set.add(line.rstrip().decode('utf-8'))
        
        self.stats["hash_time"] = time.time() - start_time
    
    def prepare(self) -> None:
        self._read_file()
    
    def search(self, query: str) -> Iterator[str]:
        super().search(query)
        start_time = time.time()
        
        if query in self._hash_set:
            yield query
        
        self.stats["search_time"] = time.time() - start_time
    
    def get_stats(self) -> dict:
        return self.stats