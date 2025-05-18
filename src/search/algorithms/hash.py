import re
import time
import os
from typing import Iterator, Dict, List, Optional, Set
import mmh3
from pybloom_live import BloomFilter
import datrie
from src.search.base import SearchAlgorithm

class HashSearch(SearchAlgorithm):
    
    def __init__(self, file_path: str, reread_on_query):
        super().__init__(file_path)
        self.stats = {"hash_time": 0, "search_time": 0}
        self._hash_set: Set[str] = set()
        self.reread_on_query = reread_on_query
        if not self.reread_on_query:
            self._read_file()
    
    def _read_file(self) -> None:
        start_time = time.time()
        self._hash_set.clear()
        
        with open(self.file_path, 'rb') as f:
            for line in f:
                self._hash_set.add(line.rstrip().decode('utf-8'))
        
        self.stats["hash_time"] = time.time() - start_time
    
    def search(self, query: str) -> bool:
        start_time = time.time()
        super().search(query)
        if self.reread_on_query:
            self._read_file()
        result = query in self._hash_set
        self.stats["search_time"] = time.time() - start_time
        return result
        
    def get_stats(self) -> dict:
        return self.stats