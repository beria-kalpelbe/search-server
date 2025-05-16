import re
import time
import os
from typing import Iterator, Dict, List, Optional, Set
import mmh3
from pybloom_live import BloomFilter
import datrie
from .base import SearchAlgorithm

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

class InMemorySearch(SearchAlgorithm):    
    def __init__(self, file_path: str):
        super().__init__(file_path)
        self.stats = {"load_time": 0, "search_time": 0}
        self._lines: Set[str] = set()
    
    def _read_file(self) -> None:
        start_time = time.time()
        with open(self.file_path, 'rb') as f:
            self._lines = {line.rstrip().decode('utf-8') for line in f}
        self.stats["load_time"] = time.time() - start_time
    
    def prepare(self) -> None:
        self._read_file()
    
    def search(self, query: str) -> Iterator[str]:
        super().search(query)
        start_time = time.time()
        
        if query in self._lines:
            yield query
        
        self.stats["search_time"] = time.time() - start_time
    
    def get_stats(self) -> dict:
        return self.stats

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

class RegexSearch(SearchAlgorithm):
    
    def __init__(self, file_path: str):
        super().__init__(file_path)
        self.stats = {"compile_time": 0, "search_time": 0}
        self._pattern: Optional[re.Pattern] = None
        self._file_size = os.path.getsize(file_path)
        self._buffer_size = min(8192, self._file_size)
    
    def _read_file(self) -> None:
        pass
    
    def prepare(self) -> None:
        pass
    
    def search(self, query: str) -> Iterator[str]:
        super().search(query)
        start_compile = time.time()
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
                        yield query
                        self.stats["search_time"] = time.time() - start_search
                        return
        
        self.stats["search_time"] = time.time() - start_search
    
    def get_stats(self) -> dict:
        return self.stats

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