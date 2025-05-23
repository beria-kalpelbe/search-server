import os
import subprocess
import time
from typing import Optional
from src.search.base import SearchAlgorithm

class GrepSearch(SearchAlgorithm):
    def __init__(self, file_path: str, reread_on_query: bool = False, case_sensitive: bool = True):
        self.file_path = file_path
        self.reread_on_query = reread_on_query
        self._lines = []
        self.case_sensitive = case_sensitive
        if not self.reread_on_query:
            self._read_file()
        

    def _grep_search(self, target: str) -> bool:
        """Use grep to check if the target string matches a whole line."""
        grep_command = ["grep", "-Fxq", target, self.file_path]
        if not self.case_sensitive:
            grep_command.insert(1, "-i")
        result = subprocess.run(
            grep_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.returncode == 0

    def search(self, target: str) -> bool:
        if not self.case_sensitive:
            target = target.lower()
        if self.reread_on_query:
            return self._grep_search(target)
        else:
            return target in self._lines
    
    def get_stats(self) -> dict:
        """
        Retrieve search statistics.

        Returns:
            dict: A dictionary containing search statistics.
        """
        return self.stats