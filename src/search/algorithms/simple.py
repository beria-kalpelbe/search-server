import re
import time
import os
from typing import Iterator, Dict, List, Optional, Set
import mmh3
from pybloom_live import BloomFilter
import datrie
from src.search.base import SearchAlgorithm

class SimpleSearch(SearchAlgorithm):    
    def __init__(self, file_path: str):
        super().__init__(file_path)
        self.stats = {"comparisons": 0, "time_taken": 0}
        self._file_size = os.path.getsize(file_path)
        self._buffer_size = min(8192, self._file_size)
    
    def prepare(self) -> None:
        pass
    
    def _read_file(self) -> None:
        pass
    
    def search(self, query: str) -> Iterator[str]:
        super().search(query)
        start_time = time.time()
        self.stats["comparisons"] = 0
        query_bytes = query.encode('utf-8') + b'\n'
        
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
                    self.stats["comparisons"] += 1
                    if line == query_bytes.rstrip():
                        yield line.decode('utf-8')
        
        self.stats["time_taken"] = time.time() - start_time
    
    def get_stats(self) -> dict:
        return self.stats