import re
import time
import os
from typing import Iterator, Dict, List, Optional, Set
import mmh3
from pybloom_live import BloomFilter
import datrie
from src.search.base import SearchAlgorithm

class RegexSearch(SearchAlgorithm):
    
    def __init__(self, file_path: str, reread_on_query: bool = False):
        super().__init__(file_path)
        self.stats = {"compile_time": 0, "search_time": 0}
        self._pattern: Optional[re.Pattern] = None
        self._file_size = os.path.getsize(file_path)
        self._buffer_size = min(8192, self._file_size)
        self.reread_on_query = reread_on_query
        if not self.reread_on_query:
            self._read_file()
    
    def _read_file(self) -> None:
        pass
    
    def search(self, query: str) -> bool:
        start_compile = time.time()
        super().search(query)
        if self.reread_on_query:
            self._read_file()
        query_bytes = query.encode('utf-8')
        self.stats["compile_time"] = time.time() - start_compile
        
        start_search = time.time()
        with open(self.file_path, 'rb') as f:
            buffer = b''
            while True:
                chunk = f.read(self._buffer_size)
                if not chunk:
                    break
                
                buffer = buffer + chunk
                lines = buffer.split(b'\n')
                buffer = lines[-1]
                
                for line in lines[:-1]:
                    if line.rstrip() == query_bytes:
                        self.stats["search_time"] = time.time() - start_search
                        return True
        
        self.stats["search_time"] = time.time() - start_search
        return False
    
    def get_stats(self) -> dict:
        return self.stats