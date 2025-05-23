import os
import time
from typing import List
from src.search.base import SearchAlgorithm

class BinarySearch(SearchAlgorithm):
    """
    Binary Search Algorithm.

    This class provides an implementation of the binary search algorithm for
    searching a query string in a sorted list of lines read from a file.

    Attributes:
        file_path (str): Path to the file to be searched.
        reread_on_query (bool): Whether to reread the file for each query.
        stats (dict): Statistics about the search process.
        _sorted_lines (List[str]): Sorted lines read from the file.
    """

    def __init__(self, file_path: str, reread_on_query: bool = False, case_sensitive:bool = True) -> None:
        """
        Initialize the BinarySearch instance.

        Args:
            file_path (str): Path to the file to be searched.
            reread_on_query (bool): Whether to reread the file for each query.
        """
        self.file_path = file_path
        self.reread_on_query = reread_on_query
        self.stats = {"comparisons": 0, "time_taken": 0.0}
        self._lines = []
        self.case_sensitive = case_sensitive
        self._sorted_lines: List[str] = []

        if not self.reread_on_query:
            self._read_and_sort_file()

    def _read_and_sort_file(self) -> None:
        """
        Read and sort the lines from the file.

        This method reads the file specified by `file_path`, decodes its lines,
        and stores them in `_sorted_lines` in sorted order.
        """
        self._read_file()
        self._sorted_lines = sorted(self._lines)

    def search(self, query: str) -> bool:
        """
        Perform a binary search for the query string.

        Args:
            query (str): The string to search for.

        Returns:
            bool: True if the query is found, False otherwise.
        """
        start_time = time.time()
        self.stats["comparisons"] = 0
        if not self.case_sensitive:
            query = query.lower()
        if self.reread_on_query:
            self._read_and_sort_file()

        left, right = 0, len(self._sorted_lines) - 1
        while left <= right:
            mid = (left + right) // 2
            self.stats["comparisons"] += 1

            if self._sorted_lines[mid] == query:
                self.stats["time_taken"] = time.time() - start_time
                return True
            elif self._sorted_lines[mid] < query:
                left = mid + 1
            else:
                right = mid - 1

        self.stats["time_taken"] = time.time() - start_time
        return False

    def get_stats(self) -> dict:
        """
        Retrieve search statistics.

        Returns:
            dict: A dictionary containing search statistics.
        """
        return self.stats