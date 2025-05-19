import time
from typing import Set
from src.search.base import SearchAlgorithm


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