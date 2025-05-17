import re
import time
import os
from typing import Iterator, Dict, List, Optional, Set
import mmh3
from pybloom_live import BloomFilter
import datrie
from src.search.base import SearchAlgorithm

class BoyerMoore(SearchAlgorithm):
    def __init__(self, file_path: str, reread_on_query: bool = False):
        super().__init__(file_path)
        self.reread_on_query = reread_on_query
        self._cache = None
        self._lines = []
        self._stats = {
            "comparisons": 0,
            "time_elapsed": 0,
            "matches_found": 0,
            "lines_processed": 0
        }
    
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
    
    def _build_bad_char_table(self, pattern: str) -> dict:
        table = {}
        pattern_length = len(pattern)
        for i in range(pattern_length - 1):
            table[pattern[i]] = pattern_length - 1 - i
        
        return table
    
    def _find_suffix_length(self, pattern: str, p: int) -> int:
        length = 0
        i = p
        j = len(pattern) - 1
        
        while i >= 0 and pattern[i] == pattern[j]:
            length += 1
            i -= 1
            j -= 1
        
        return length
    
    def _is_prefix(self, pattern: str, p: int) -> bool:
        for i, j in zip(range(p, len(pattern)), range(len(pattern) - p)):
            if pattern[i] != pattern[j]:
                return False
        return True
    
    def _build_good_suffix_table(self, pattern: str) -> List[int]:
        pattern_length = len(pattern)
        table = [0] * pattern_length
        last_prefix_position = pattern_length
        
        for i in range(pattern_length - 1, -1, -1):
            if self._is_prefix(pattern, i + 1):
                last_prefix_position = i + 1
            table[pattern_length - 1 - i] = last_prefix_position - i + pattern_length - 1
        
        for i in range(pattern_length - 1):
            suffix_length = self._find_suffix_length(pattern, i)
            if suffix_length > 0:
                table[suffix_length] = pattern_length - 1 - i + suffix_length
        
        return table
    
    def search(self, query: str) -> Iterator[str]:
        if self.reread_on_query:
            self._read_file()
        if not self._cache:
            self._read_file()
        self._stats["comparisons"] = 0
        self._stats["matches_found"] = 0
        self._stats["time_elapsed"] = 0
        start_time = time.time()        
        bad_char_table = self._build_bad_char_table(query)
        good_suffix_table = self._build_good_suffix_table(query)
        for line_index, line in enumerate(self._lines):
            if len(line) != len(query):
                continue
            i = len(query) - 1
            while i < len(line):
                j = len(query) - 1
                k = i
                while j >= 0 and line[k] == query[j]:
                    self._stats["comparisons"] += 1
                    k -= 1
                    j -= 1
                if j == -1:
                    self._stats["matches_found"] += 1
                    yield line
                    break
                self._stats["comparisons"] += 1
                bad_char_shift = bad_char_table.get(line[k], len(query))
                good_suffix_shift = good_suffix_table[len(query) - 1 - j]
                i += max(bad_char_shift, good_suffix_shift)
        self._stats["time_elapsed"] = time.time() - start_time
    
    def get_stats(self) -> dict:
        return self._stats