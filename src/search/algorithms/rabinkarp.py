import time
from src.search.base import SearchAlgorithm

class RabinKarp(SearchAlgorithm):
    """
    RabinKarp Algorithm Implementation for String Search

    This class implements the Rabin-Karp string searching algorithm, which uses
    hashing to find patterns in text. It extends the SearchAlgorithm base class
    to provide efficient string matching functionality.

    The Rabin-Karp algorithm works by using a rolling hash function to quickly
    compare substrings against a pattern, only performing character-by-character
    comparison when hash values match, making it efficient for multiple pattern
    searches.

    Args:
        file_path (str): Path to the file to search in
        reread_on_query (bool, optional): Whether to reread the file for each query. Defaults to False.
        base (int, optional): Base value for the hash function. Defaults to 256.
        prime (int, optional): Prime number for the hash function modulus. Defaults to 101.

    Attributes:
        reread_on_query (bool): Flag indicating whether to reread the file on each query
        _lines (List[str]): Lines of the file stored for searching
        _stats (Dict): Dictionary tracking search statistics including comparisons,
                    time elapsed, lines processed, and hash collisions
        base (int): Base value for the polynomial hash function
        prime (int): Prime number used as modulus in hash calculations

    Methods:
        _read_file(): Reads and processes the file specified in file_path
        _calculate_hash(string, length): Calculates the hash value for a given string
        _recalculate_hash(old_hash, old_char, new_char, pattern_length): Recalculates hash when sliding window
        _check_strings(text, pattern, start): Performs character-by-character comparison
        search(query): Searches for the provided query string in the file
        get_stats(): Returns statistics about the last search operation

    Example:
        >>> rk = RabinKarp('/path/to/file.txt')
        >>> rk.search('pattern')
        True
        >>> rk.get_stats()
        {'comparisons': 12, 'time_elapsed': 0.0005, 'lines_processed': 1000, 'hash_collisions': 0}
    """
    def __init__(self, file_path: str, reread_on_query: bool = False, base: int = 256, prime: int = 101, case_sensitive: bool = True) -> None:
        super().__init__(file_path)
        self.reread_on_query = reread_on_query
        self._stats = {
            "comparisons": 0,
            "time_elapsed": 0,
            "lines_processed": 0,
            "hash_collisions": 0
        }
        self.base = base
        self.prime = prime 
        self.case_sensitive = case_sensitive
        if not self.reread_on_query:
            self._read_file()
    
    
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
    
    def search(self, query: str) -> bool:
        start_time = time.time()
        super().search(query)
        if self.reread_on_query:
            self._read_file()
        
        self._stats["comparisons"] = 0
        self._stats["time_elapsed"] = 0
        self._stats["hash_collisions"] = 0
        
        result = False
        for line in self._lines:
            if len(line) != len(query):
                continue
            if not self.case_sensitive:
                line = line.lower()
                query = query.lower()
            line_hash = self._calculate_hash(line, len(query))
            query_hash = self._calculate_hash(query, len(query))
            
            if line_hash == query_hash:
                if self._check_strings(line, query, 0):
                    return True
                else:
                    self._stats["hash_collisions"] += 1
        self._stats["time_elapsed"] = time.time() - start_time
        return result
    
    def get_stats(self) -> dict:
        return self._stats