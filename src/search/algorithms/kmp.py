import re
import time
import os
from typing import Iterator, Dict, List, Optional, Set
import mmh3
from pybloom_live import BloomFilter
import datrie
from src.search.base import SearchAlgorithm

class KMP(SearchAlgorithm):
    """
    KMP (Knuth-Morris-Pratt) string search algorithm implementation.
    This class implements the KMP algorithm for efficient substring search within
    a text file. It extends the `SearchAlgorithm` base class and provides methods
    to preprocess the input file, compute the prefix table (LPS array), and perform
    the search operation.
    Attributes:
        reread_on_query (bool): Determines whether the file should be re-read on
            every search query. Defaults to False.
        _lines (List[str]): List of lines from the file.
        _stats (dict): Dictionary to store statistics about the search process,
            including the number of comparisons, search time, lines processed,
            and prefix table computations.
    """
    def __init__(self, file_path: str, reread_on_query: bool = False, case_sensitive: bool = True) -> None:
        """
        Initializes the KMP (Knuth-Morris-Pratt) search algorithm instance.

        Args:
            file_path (str): The path to the file that will be processed for search operations.
            reread_on_query (bool, optional): If True, the file will be re-read on each query. 
                Defaults to False.
        """
        super().__init__(file_path)
        self.reread_on_query = reread_on_query
        self.case_sensitive = case_sensitive
        self._stats = {
            "comparisons": 0,
            "search_time": 0,
            "lines_processed": 0,
            "prefix_table_computations": 0
        }
        if not self.reread_on_query:
            self._read_file()
    
    
    def _compute_lps(self, pattern: str) -> List[int]:
        length = len(pattern)
        lps = [0] * length 
        
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
    
    def search(self, query: str) -> bool:
        start_time = time.time()
        super().search(query)
        if self.reread_on_query:
            self._read_file()
        
        self._stats["comparisons"] = 0
        self._stats["search_time"] = 0
        self._stats["prefix_table_computations"] = 0
        
        for line in self._lines:
            if not self.case_sensitive:
                line = line.lower()
                query = query.lower()
            if self._kmp_search(line, query):
                return True
        self._stats["search_time"] = time.time() - start_time
        return False
    
    def get_stats(self) -> dict:
        return self._stats
