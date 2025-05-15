import pytest
from src.search.algorithms import (
    SimpleSearch,
    InMemorySearch,
    BinarySearch,
    HashSearch,
    RegexSearch,
    BloomFilterSearch
)

@pytest.fixture
def test_data():
    return [
        "The quick brown fox jumps over the lazy dog",
        "Python is a great programming language",
        "Algorithms and data structures are fundamental",
        "Testing is important for software quality",
        "Search algorithms have different complexities"
    ]

@pytest.fixture
def search_algorithms():
    return [
        SimpleSearch(),
        InMemorySearch(),
        BinarySearch(),
        HashSearch(),
        RegexSearch(),
        BloomFilterSearch()
    ]

def test_exact_match(test_data, search_algorithms):
    for algo in search_algorithms:
        algo.build_index(test_data)
        results = algo.search("Python")
        assert len(results) == 1
        assert "Python is a great programming language" in results

def test_case_insensitive(test_data, search_algorithms):
    for algo in search_algorithms:
        algo.build_index(test_data)
        results = algo.search("python", case_sensitive=False)
        assert len(results) == 1
        assert "Python is a great programming language" in results

def test_multiple_matches(test_data, search_algorithms):
    for algo in search_algorithms:
        algo.build_index(test_data)
        results = algo.search("algorithms", case_sensitive=False)
        assert len(results) == 2

def test_no_matches(test_data, search_algorithms):
    for algo in search_algorithms:
        algo.build_index(test_data)
        results = algo.search("nonexistent")
        assert len(results) == 0

def test_empty_query(test_data, search_algorithms):
    for algo in search_algorithms:
        algo.build_index(test_data)
        with pytest.raises(ValueError):
            algo.search("")

def test_build_index_empty_data(search_algorithms):
    for algo in search_algorithms:
        with pytest.raises(ValueError):
            algo.build_index([]) 