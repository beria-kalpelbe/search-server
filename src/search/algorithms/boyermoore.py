import re
import time
import os
from typing import Iterator, Dict, List, Optional, Set
import mmh3
from pybloom_live import BloomFilter
import datrie
from src.search.base import SearchAlgorithm

class BoyerMoore(SearchAlgorithm):
    """
    
    Boyer-Moore string search algorithm implementation.
    This class implements the Boyer-Moore algorithm for efficient substring search within
    a text file. It extends the `SearchAlgorithm` base class and provides methods
    to preprocess the input file, compute the bad character and good suffix tables,
    and perform the search operation.
    
    Attributes:
        reread_on_query (bool): Determines whether the file should be re-read on
            every search query. Defaults to False.
        _cache (str): Cached content of the file.
        _lines (List[str]): List of lines from the file.
        _stats (dict): Dictionary to store statistics about the search process,
            including the number of comparisons, search time, and lines processed.
            
        pattern_length (int): Length of the search pattern.
        search_results (List[int]): List to store the indices of found occurrences.
        
    Methods:
        _read_file(): Reads the file and populates the _lines attribute.
        _build_bad_char_table(pattern: str) -> dict: Builds the bad character table.
        _find_suffix_length(pattern: str, p: int) -> int: Finds the length of the suffix.
        _is_prefix(pattern: str, p: int) -> bool: Checks if a substring is a prefix.
        _build_good_suffix_table(pattern: str) -> List[int]: Builds the good suffix table.
        search(query: str) -> bool: Searches for the provided query string in the file.
        get_stats() -> dict: Returns statistics about the last search operation.
    """
    def __init__(self, file_path: str, reread_on_query: bool = False):
        super().__init__(file_path)
        self.reread_on_query = reread_on_query
        self._cache = None
        self._lines = []
        self._stats = {
            "comparisons": 0,
            "search_time": 0,
            "lines_processed": 0
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
    
    def search(self, query: str) -> bool:
        start_time = time.time()
        super().search(query)
        if self.reread_on_query:
            self._read_file()
        if not self._cache:
            self._read_file()
        self._stats["comparisons"] = 0
        self._stats["search_time"] = 0
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
                    self._stats["search_time"] = time.time() - start_time
                    return True
                self._stats["comparisons"] += 1
                bad_char_shift = bad_char_table.get(line[k], len(query))
                good_suffix_shift = good_suffix_table[len(query) - 1 - j]
                i += max(bad_char_shift, good_suffix_shift)
        self._stats["search_time"] = time.time() - start_time
        return False
    
    def get_stats(self) -> dict:
        return self._stats


class HashSearch(SearchAlgorithm):
    """
    Hash-Based Search Algorithm.

    This class provides an implementation of a search algorithm using a hash
    set for efficient membership testing.

    Attributes:
        file_path (str): Path to the file to be searched.
        reread_on_query (bool): Whether to reread the file for each query.
        stats (dict): Statistics about the search process.
        _hash_set (Set[str]): A set of hashed lines read from the file.
    """

    def __init__(self, file_path: str, reread_on_query: bool = False) -> None:
        """
        Initialize the HashSearch instance.

        Args:
            file_path (str): Path to the file to be searched.
            reread_on_query (bool): Whether to reread the file for each query.
        """
        super().__init__(file_path)
        self.stats = {"hash_time": 0.0, "search_time": 0.0}
        self._hash_set: Set[str] = set()
        self.reread_on_query = reread_on_query

        if not self.reread_on_query:
            self._read_file()

    def _read_file(self) -> None:
        """
        Read the file and populate the hash set.

        This method reads the file specified by `file_path`, decodes its lines,
        and adds them to the `_hash_set`.
        """
        start_time = time.time()
        self._hash_set.clear()

        try:
            with open(self.file_path, 'rb') as file:
                for line in file:
                    self._hash_set.add(line.rstrip().decode('utf-8'))
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {self.file_path}")
        except Exception as e:
            raise RuntimeError(f"Error reading file: {e}")

        self.stats["hash_time"] = time.time() - start_time

    def search(self, query: str) -> bool:
        """
        Perform a search for the query string using the hash set.

        Args:
            query (str): The string to search for.

        Returns:
            bool: True if the query is found, False otherwise.
        """
        start_time = time.time()

        if self.reread_on_query:
            self._read_file()

        result = query in self._hash_set
        self.stats["search_time"] = time.time() - start_time
        return result

    def get_stats(self) -> dict:
        """
        Retrieve search statistics.

        Returns:
            dict: A dictionary containing search statistics.
        """
        return self.stats