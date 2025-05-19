import re
import time
import os
from typing import Iterator, Dict, List, Optional, Set
import mmh3
from pybloom_live import BloomFilter
import datrie
from src.search.base import SearchAlgorithm

class KMP(SearchAlgorithm):
    def __init__(self, file_path: str, reread_on_query: bool = False):
        super().__init__(file_path)
        self.reread_on_query = reread_on_query
        self._cache = None
        self._lines = []
        self._stats = {
            "comparisons": 0,
            "search_time": 0,
            "lines_processed": 0,
            "prefix_table_computations": 0
        }
        if not self.reread_on_query:
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
    
    def _compute_lps(self, pattern: str) -> List[int]:
        length = len(pattern)
        lps = [0] * length  # lps[0] is always 0
        
        len_prev_lps = 0
        i = 1
        while i < length:
            self._stats["prefix_table_computations"] += 1
            if pattern[i] == pattern[len_prev_lps]:
                len_prev_lps += 1
                lps[i] = len_prev_lps
                i += 1
            elif len_prev_lps > 0:
                len_prev_lps = lps[len_prev_lps - 1]
            else:
                lps[i] = 0
                i += 1
        
        return lps
    
    def _kmp_search(self, text: str, pattern: str) -> bool:
        if len(text) != len(pattern):
            return False
        m = len(pattern)
        n = len(text)
        
        lps = self._compute_lps(pattern)
        
        i = 0  # Index for text
        j = 0  # Index for pattern
        
        while i < n:
            self._stats["comparisons"] += 1
            
            if pattern[j] == text[i]:
                i += 1
                j += 1
            if j == m:
                return True
            elif i < n and pattern[j] != text[i]:
                if j > 0:
                    j = lps[j - 1]
                else:
                    i += 1
        
        return False
    
    def search(self, query: str) -> Iterator[str]:
        start_time = time.time()
        super().search(query)
        if self.reread_on_query:
            self._read_file()
        
        if not self._cache:
            self._read_file()
        
        self._stats["comparisons"] = 0
        self._stats["search_time"] = 0
        self._stats["prefix_table_computations"] = 0
        
        result = False
        for line in self._lines:
            if self._kmp_search(line, query):
                return True
        self._stats["search_time"] = time.time() - start_time
        return result
    
    def get_stats(self) -> dict:
        return self._stats
