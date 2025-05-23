import time
from typing import Set
from pybloom_live import BloomFilter
from src.search.base import SearchAlgorithm


class BloomFilterSearch(SearchAlgorithm):
    """
    Bloom Filter Search Algorithm.

    This class provides an implementation of a search algorithm using a Bloom
    filter for efficient membership testing.

    Attributes:
        file_path (str): Path to the file to be searched.
        reread_on_query (bool): Whether to reread the file for each query.
        stats (dict): Statistics about the search process.
        _bloom (BloomFilter): The Bloom filter used for membership testing.
        _lines (Set[str]): A set of lines read from the file.
    """

    def __init__(
        self,
        file_path: str,
        reread_on_query: bool = False,
        capacity: int = 1_000_000,
        error_rate: float = 0.001,
        case_sensitive: bool = True
    ) -> None:
        """
        Initialize the BloomFilterSearch instance.

        Args:
            file_path (str): Path to the file to be searched.
            reread_on_query (bool): Whether to reread the file for each query.
            capacity (int): The capacity of the Bloom filter.
            error_rate (float): The acceptable error rate for the Bloom filter.
        """
        super().__init__(file_path)
        self.stats = {"search_time": 0.0}
        self._bloom = BloomFilter(capacity=capacity, error_rate=error_rate)
        self._lines: Set[str] = set()
        self.case_sensitive = case_sensitive
        self.reread_on_query = reread_on_query

        if not self.reread_on_query:
            self._read_file()

    def _read_file(self) -> None:
        """
        Read the file and populate the Bloom filter and line set.

        This method reads the file specified by `file_path`, decodes its lines,
        and adds them to the Bloom filter and the `_lines` set.
        """
        try:
            with open(self.file_path, 'rb') as file:
                self._bloom = BloomFilter(capacity=1_000_000, error_rate=0.001)
                self._lines.clear()
                for line in file:
                    line_str = line.rstrip().decode('utf-8')
                    if not self.case_sensitive:
                        line_str = line_str.lower()
                    self._bloom.add(line_str)
                    self._lines.add(line_str)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {self.file_path}")
        except Exception as e:
            raise RuntimeError(f"Error reading file: {e}")

    def search(self, query: str) -> bool:
        """
        Perform a search for the query string using the Bloom filter.

        Args:
            query (str): The string to search for.

        Returns:
            bool: True if the query is found, False otherwise.
        """
        start_time = time.time()

        if self.reread_on_query:
            self._read_file()
        if not self.case_sensitive:
            query = query.lower()
        result = query in self._bloom and query in self._lines
        self.stats["search_time"] = time.time() - start_time
        return result

    def get_stats(self) -> dict:
        """
        Retrieve search statistics.

        Returns:
            dict: A dictionary containing search statistics.
        """
        return self.stats