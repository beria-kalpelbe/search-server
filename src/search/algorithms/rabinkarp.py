import re
import time
import os
from typing import Iterator, Dict, List, Optional, Set
import mmh3
from pybloom_live import BloomFilter
import datrie
from src.search.base import SearchAlgorithm

class RabinKarp(SearchAlgorithm):
    def __init__(self, file_path: str, reread_on_query: bool = False, base: int = 256, prime: int = 101):
        super().__init__(file_path)
        self.reread_on_query = reread_on_query
        self._cache = None
        self._lines = []
        self._stats = {
            "comparisons": 0,
            "time_elapsed": 0,
            "matches_found": 0,
            "lines_processed": 0,
            "hash_collisions": 0
        }
        self.base = base
        self.prime = prime 
    
    def prepare(self) -> None:
        self._read_file()
    
    def _read_file(self) -> None:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                self._cache = file.read()
                self._lines = self._cache.split('\n')
                self._stats["lines_processed"] = len(self._lines)
        except FileNotFoundError:
            print(f"Error: File '{self.file_path}' not found.")
            self._cache = ""
            self._lines = []
        except Exception as e:
            print(f"Error reading file: {str(e)}")
            self._cache = ""
            self._lines = []
    
    def _calculate_hash(self, string: str, length: int) -> int:
        hash_value = 0
        
        for i in range(length):
            hash_value = (hash_value * self.base + ord(string[i])) % self.prime
            
        return hash_value
    
    def _recalculate_hash(self, old_hash: int, old_char: str, new_char: str, pattern_length: int) -> int:
        new_hash = (old_hash - ord(old_char) * pow(self.base, pattern_length - 1, self.prime)) % self.prime
        
        new_hash = (new_hash * self.base + ord(new_char)) % self.prime
        
        if new_hash < 0:
            new_hash += self.prime
            
        return new_hash
    
    def _check_strings(self, text: str, pattern: str, start: int) -> bool:
        for i in range(len(pattern)):
            self._stats["comparisons"] += 1
            if text[start + i] != pattern[i]:
                return False
        return True
    
    def search(self, query: str) -> Iterator[str]:
        if self.reread_on_query:
            self._read_file()
        
        if not self._cache:
            self._read_file()
        
        self._stats["comparisons"] = 0
        self._stats["matches_found"] = 0
        self._stats["time_elapsed"] = 0
        self._stats["hash_collisions"] = 0
        
        start_time = time.time()
        
        for line in self._lines:
            if len(line) != len(query):
                continue
            
            line_hash = self._calculate_hash(line, len(query))
            query_hash = self._calculate_hash(query, len(query))
            
            if line_hash == query_hash:
                if self._check_strings(line, query, 0):
                    self._stats["matches_found"] += 1
                    yield line
                else:
                    self._stats["hash_collisions"] += 1
        
        self._stats["time_elapsed"] = time.time() - start_time
    
    def get_stats(self) -> dict:
        """Get statistics about the last search operation."""
        return self._stats