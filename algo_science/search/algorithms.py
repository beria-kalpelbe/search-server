"""Implementation of various search algorithms."""

import re
import time
from typing import Iterator, Dict, List, Optional
import mmh3
from pybloom_live import BloomFilter
import datrie
from .base import SearchAlgorithm

class SimpleSearch(SearchAlgorithm):
    """Simple line-by-line search algorithm."""
    
    def __init__(self, file_path: str):
        super().__init__(file_path)
        self.stats = {"comparisons": 0, "time_taken": 0}
    
    def prepare(self) -> None:
        """No preparation needed for simple search."""
        pass
    
    def search(self, query: str) -> Iterator[str]:
        start_time = time.time()
        self.stats["comparisons"] = 0
        
        with open(self.file_path, 'r') as f:
            for line in f:
                self.stats["comparisons"] += 1
                if query in line:
                    yield line.rstrip()
        
        self.stats["time_taken"] = time.time() - start_time
    
    def get_stats(self) -> dict:
        return self.stats

class InMemorySearch(SearchAlgorithm):
    """In-memory full file search."""
    
    def __init__(self, file_path: str):
        super().__init__(file_path)
        self.stats = {"load_time": 0, "search_time": 0}
        self._lines: List[str] = []
    
    def prepare(self) -> None:
        start_time = time.time()
        with open(self.file_path, 'r') as f:
            self._lines = f.readlines()
        self.stats["load_time"] = time.time() - start_time
    
    def search(self, query: str) -> Iterator[str]:
        start_time = time.time()
        
        for line in self._lines:
            if query in line:
                yield line.rstrip()
        
        self.stats["search_time"] = time.time() - start_time
    
    def get_stats(self) -> dict:
        return self.stats

class BinarySearch(SearchAlgorithm):
    """Binary search for sorted files."""
    
    def __init__(self, file_path: str):
        super().__init__(file_path)
        self.stats = {"comparisons": 0, "time_taken": 0}
        self._sorted_lines: List[str] = []
    
    def prepare(self) -> None:
        with open(self.file_path, 'r') as f:
            self._sorted_lines = sorted(f.readlines())
    
    def search(self, query: str) -> Iterator[str]:
        start_time = time.time()
        self.stats["comparisons"] = 0
        
        left, right = 0, len(self._sorted_lines) - 1
        while left <= right:
            mid = (left + right) // 2
            self.stats["comparisons"] += 1
            
            if query in self._sorted_lines[mid]:
                # Search around the found position
                yield self._sorted_lines[mid].rstrip()
                
                # Check surrounding lines
                i = mid - 1
                while i >= 0 and query in self._sorted_lines[i]:
                    yield self._sorted_lines[i].rstrip()
                    i -= 1
                
                i = mid + 1
                while i < len(self._sorted_lines) and query in self._sorted_lines[i]:
                    yield self._sorted_lines[i].rstrip()
                    i += 1
                break
            
            elif self._sorted_lines[mid] < query:
                left = mid + 1
            else:
                right = mid - 1
        
        self.stats["time_taken"] = time.time() - start_time
    
    def get_stats(self) -> dict:
        return self.stats

class HashSearch(SearchAlgorithm):
    """Hash-based search using MurmurHash3."""
    
    def __init__(self, file_path: str):
        super().__init__(file_path)
        self.stats = {"hash_time": 0, "search_time": 0}
        self._hash_table: Dict[int, List[str]] = {}
    
    def prepare(self) -> None:
        start_time = time.time()
        
        with open(self.file_path, 'r') as f:
            for line in f:
                # Hash each word in the line
                for word in line.split():
                    hash_val = mmh3.hash(word)
                    if hash_val not in self._hash_table:
                        self._hash_table[hash_val] = []
                    self._hash_table[hash_val].append(line.rstrip())
        
        self.stats["hash_time"] = time.time() - start_time
    
    def search(self, query: str) -> Iterator[str]:
        start_time = time.time()
        
        hash_val = mmh3.hash(query)
        if hash_val in self._hash_table:
            seen = set()
            for line in self._hash_table[hash_val]:
                if line not in seen and query in line:
                    seen.add(line)
                    yield line
        
        self.stats["search_time"] = time.time() - start_time
    
    def get_stats(self) -> dict:
        return self.stats

class RegexSearch(SearchAlgorithm):
    """Regex-based search."""
    
    def __init__(self, file_path: str):
        super().__init__(file_path)
        self.stats = {"compile_time": 0, "search_time": 0}
        self._pattern: Optional[re.Pattern] = None
    
    def prepare(self) -> None:
        """No preparation needed until search pattern is known."""
        pass
    
    def search(self, query: str) -> Iterator[str]:
        start_compile = time.time()
        self._pattern = re.compile(re.escape(query))
        self.stats["compile_time"] = time.time() - start_compile
        
        start_search = time.time()
        with open(self.file_path, 'r') as f:
            for line in f:
                if self._pattern.search(line):
                    yield line.rstrip()
        
        self.stats["search_time"] = time.time() - start_search
    
    def get_stats(self) -> dict:
        return self.stats

class BloomFilterSearch(SearchAlgorithm):
    """Bloom filter based search."""
    
    def __init__(self, file_path: str, capacity: int = 1000000, error_rate: float = 0.001):
        super().__init__(file_path)
        self.stats = {"filter_build_time": 0, "search_time": 0}
        self._bloom = BloomFilter(capacity=capacity, error_rate=error_rate)
        self._line_map: Dict[str, List[str]] = {}
    
    def prepare(self) -> None:
        start_time = time.time()
        
        with open(self.file_path, 'r') as f:
            for line in f:
                for word in line.split():
                    self._bloom.add(word)
                    if word not in self._line_map:
                        self._line_map[word] = []
                    self._line_map[word].append(line.rstrip())
        
        self.stats["filter_build_time"] = time.time() - start_time
    
    def search(self, query: str) -> Iterator[str]:
        start_time = time.time()
        
        if query in self._bloom:
            seen = set()
            for word in query.split():
                if word in self._line_map:
                    for line in self._line_map[word]:
                        if line not in seen and query in line:
                            seen.add(line)
                            yield line
        
        self.stats["search_time"] = time.time() - start_time
    
    def get_stats(self) -> dict:
        return self.stats 