from abc import ABC, abstractmethod
from typing import Iterator, Optional, List

class SearchAlgorithm(ABC):
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._cache = None
        self.reread_on_query = False
    
    # @abstractmethod
    # def prepare(self) -> None:
    #     pass
    
    @abstractmethod
    def _read_file(self) -> None:
        pass
    
    @abstractmethod
    def search(self, query: str) -> Iterator[str]:
        if self.reread_on_query:
            self._read_file()
        pass
    
    @abstractmethod
    def get_stats(self) -> dict:
        pass
    
    def cleanup(self) -> None:
        if hasattr(self, '_cache'):
            self._cache = None 