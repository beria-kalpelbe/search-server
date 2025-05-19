import pytest
import os
import time





import unittest
import tempfile
import os
import time
from abc import ABC, abstractmethod
from typing import Type

class BaseSearchAlgorithmTest(ABC):
    """Abstract base class for testing search algorithms"""
    
    @abstractmethod
    def get_search_class(self):
        """Return the search algorithm class to test"""
        pass
    
    @abstractmethod
    def get_default_kwargs(self):
        """Return default kwargs for the search algorithm"""
        return {}
    
    def setUp(self):
        # Create a temporary file with test data
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = os.path.join(self.temp_dir.name, "test_data.txt")
        
        # Create test data
        test_data = [
            "apple",
            "banana",
            "cherry",
            "date",
            "elderberry",
            "fig",
            "grape",
            "honeydew"
        ]
        
        with open(self.test_file, 'wb') as f:
            for item in test_data:
                f.write(f"{item}\n".encode('utf-8'))
    
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def test_init_with_default_parameters(self):
        """Test initialization with default parameters"""
        search = self.get_search_class()(self.test_file, **self.get_default_kwargs())
        self.assertFalse(search.reread_on_query)
        
        # Verify stats are initialized
        stats = search.get_stats()
        self.assertGreaterEqual(self.get_initial_stat_value(stats), 0)
    
    @abstractmethod
    def get_initial_stat_value(self, stats):
        """Return the initial stat value that should be >= 0"""
        pass
    
    def test_search_existing_items(self):
        """Test searching for items that exist"""
        search = self.get_search_class()(self.test_file, **self.get_default_kwargs())
        
        # Test all items
        self.assertTrue(search.search("apple"))
        self.assertTrue(search.search("banana"))
        self.assertTrue(search.search("honeydew"))
    
    def test_search_non_existing_items(self):
        """Test searching for items that don't exist"""
        search = self.get_search_class()(self.test_file, **self.get_default_kwargs())
        
        # Test non-existing items
        self.assertFalse(search.search("kiwi"))
        self.assertFalse(search.search("orange"))
        self.assertFalse(search.search("watermelon"))
    
    def test_search_with_reread(self):
        """Test that file is reread when reread_on_query=True"""
        search = self.get_search_class()(self.test_file, reread_on_query=True, **self.get_default_kwargs())
        
        # Verify initial state based on algorithm
        self.verify_initial_reread_state(search)
        
        # First search should load data
        self.assertTrue(search.search("banana"))
        self.verify_post_first_search_state(search)
        
        # Modify the file
        with open(self.test_file, 'ab') as f:
            f.write(b"kiwi\n")
        
        # Next search should reload and find new item
        self.assertTrue(search.search("kiwi"))
        self.verify_post_modification_state(search)
    
    @abstractmethod
    def verify_initial_reread_state(self, search):
        """Verify the initial state when reread_on_query=True"""
        pass
    
    @abstractmethod
    def verify_post_first_search_state(self, search):
        """Verify state after first search with reread_on_query=True"""
        pass
    
    @abstractmethod
    def verify_post_modification_state(self, search):
        """Verify state after file modification and search"""
        pass
    
    def test_empty_file(self):
        """Test behavior with empty file"""
        empty_file = os.path.join(self.temp_dir.name, "empty.txt")
        with open(empty_file, 'wb') as f:
            pass
        
        search = self.get_search_class()(empty_file, **self.get_default_kwargs())
        self.assertFalse(search.search("anything"))
    
    def test_case_sensitivity(self):
        """Test that search is case sensitive"""
        search = self.get_search_class()(self.test_file, **self.get_default_kwargs())
        
        # Different case should not match
        self.assertFalse(search.search("Apple"))
        self.assertFalse(search.search("BANANA"))
        
        # Exact case should match
        self.assertTrue(search.search("apple"))
        self.assertTrue(search.search("banana"))





class TestBinarySearch(BaseSearchAlgorithmTest, unittest.TestCase):
    """Concrete test class for BinarySearch"""
    
    def get_search_class(self):
        from src.search.algorithms.binary import BinarySearch
        return BinarySearch
    
    def get_default_kwargs(self):
        return {}
    
    def get_initial_stat_value(self, stats):
        return stats["time_taken"]
    
    # def get_search_stat_value(self, stats):
    #     return stats["time_taken"]
    
    def verify_initial_reread_state(self, search):
        self.assertEqual(len(search._sorted_lines), 0)
    
    def verify_post_first_search_state(self, search):
        self.assertEqual(len(search._sorted_lines), 8)
    
    def verify_post_modification_state(self, search):
        self.assertEqual(len(search._sorted_lines), 9)
    
    def test_search_comparisons(self):
        """BinarySearch specific test for comparison counting"""
        search = self.get_search_class()(self.test_file)
        search.search("date")
        stats = search.get_stats()
        self.assertGreater(stats["comparisons"], 0)
        self.assertLess(stats["comparisons"], 4)  # log2(8) = 3 max


class TestBloomFilterSearch(BaseSearchAlgorithmTest, unittest.TestCase):
    """Concrete test class for BloomFilterSearch"""
    
    def get_search_class(self):
        from src.search.algorithms.bloomfilter import BloomFilterSearch
        return BloomFilterSearch
    
    def get_default_kwargs(self):
        return {"capacity": 1000000, "error_rate": 0.001}
    
    # def get_search_stat_value(self, stats):
    #     return stats["search_time"]
    
    def verify_initial_reread_state(self, search):
        self.assertEqual(len(search._lines), 0)
    
    def verify_post_first_search_state(self, search):
        self.assertEqual(len(search._lines), 9)
    
    def verify_post_modification_state(self, search):
        self.assertEqual(len(search._lines), 9)
    
    def test_false_positives(self):
        """BloomFilter specific test for false positives"""
        # Create a large test file
        large_file = os.path.join(self.temp_dir.name, "large.txt")
        with open(large_file, 'wb') as f:
            for i in range(10000):
                f.write(f"word_{i}\n".encode('utf-8'))
        
        search = self.get_search_class()(large_file, error_rate=0.01)
        
        # Test non-existing items that might cause false positives
        false_positives = 0
        tests = 1000
        for i in range(10000, 10000 + tests):
            if search.search(f"word_{i}"):
                false_positives += 1
        
        # Verify false positive rate is within expected bounds
        false_positive_rate = false_positives / tests
        self.assertLess(false_positive_rate, 0.02)  # Allow some margin
        

class TestBoyerMoore(BaseSearchAlgorithmTest, unittest.TestCase):
    """Concrete test class for BoyerMoore search algorithm"""
    
    def get_search_class(self):
        from src.search.algorithms.boyermoore import BoyerMoore
        return BoyerMoore
    
    def get_default_kwargs(self):
        return {}
    
    def get_initial_stat_value(self, stats):
        return stats["lines_processed"]
    
    # def get_search_stat_value(self, stats):
    #     return stats["search_time"]
    
    def verify_initial_reread_state(self, search):
        self.assertEqual(len(search._lines), 0)
        self.assertIsNone(search._cache)
    
    def verify_post_first_search_state(self, search):
        # 8 lines + 1 empty from trailing newline
        self.assertEqual(len(search._lines), 9)
        self.assertIsNotNone(search._cache)
    
    def verify_post_modification_state(self, search):
        # 8 original + 1 new + 1 empty from trailing newline
        self.assertEqual(len(search._lines), 10)
        self.assertIsNotNone(search._cache)
    
    def test_boyer_moore_specific_behavior(self):
        """Test Boyer-Moore specific pattern matching behavior"""
        # Create a test file without trailing newline
        pattern_file = os.path.join(self.temp_dir.name, "pattern_test.txt")
        with open(pattern_file, 'w', encoding='utf-8') as f:
            f.write("ABACADABRAC\nTESTTESTTEST\nMISSISSIPPI\nABCDEFGHIJKL")  # No trailing \n
        
        bm = self.get_search_class()(pattern_file)
        
        # Should have exactly 4 lines
        self.assertEqual(len(bm._lines), 4)
        
        # Test exact matches
        self.assertTrue(bm.search("ABACADABRAC"))
        self.assertTrue(bm.search("TESTTESTTEST"))
        self.assertTrue(bm.search("MISSISSIPPI"))
        
        # Test non-matches
        self.assertFalse(bm.search("ABACADABRA"))
        self.assertFalse(bm.search("ABACADABRACD"))
        self.assertFalse(bm.search("TESTTESTTES"))
        
        # Verify stats
        stats = bm.get_stats()
        self.assertGreater(stats["comparisons"], 0)
        self.assertGreater(stats["search_time"], 0)
    
    def test_bad_char_table(self):
        """Test the bad character table construction"""
        bm = self.get_search_class()(self.test_file)
        table = bm._build_bad_char_table("ABCDABD")
        expected = {
            'A': 2,
            'B': 1,
            'C': 4,
            'D': 3
        }
        self.assertEqual(table, expected)
    
    def test_good_suffix_table(self):
        """Test the good suffix table construction"""
        bm = self.get_search_class()(self.test_file)
        table = bm._build_good_suffix_table("ABABCBAB")
        self.assertEqual(len(table), 8)
        self.assertGreater(table[0], 0)
    
    def test_is_prefix(self):
        """Test the prefix detection helper"""
        bm = self.get_search_class()(self.test_file)
        self.assertTrue(bm._is_prefix("TESTTEST", 4))
        self.assertFalse(bm._is_prefix("TESTTEST", 5))
        self.assertTrue(bm._is_prefix("ABCABC", 3))
    
    def test_find_suffix_length(self):
        """Test the suffix length helper"""
        bm = self.get_search_class()(self.test_file)
        self.assertEqual(bm._find_suffix_length("ABCABC", 2), 3)
        self.assertEqual(bm._find_suffix_length("ABCDEF", 2), 0)
        self.assertEqual(bm._find_suffix_length("ABABAB", 4), 0)
    
    def test_partial_matches(self):
        """Test behavior with partial matches"""
        partial_file = os.path.join(self.temp_dir.name, "partial.txt")
        with open(partial_file, 'w', encoding='utf-8') as f:
            f.write("PARTIAL_MATCH_TEST\nTHIS_IS_A_TEST\nTESTING_PARTIAL_MATCHES")
        
        bm = self.get_search_class()(partial_file)
        self.assertEqual(len(bm._lines), 3)
        self.assertFalse(bm.search("PARTIAL"))
        self.assertFalse(bm.search("TEST"))
        self.assertTrue(bm.search("THIS_IS_A_TEST"))
        self.assertTrue(bm.search("TESTING_PARTIAL_MATCHES"))
        
 
class TestHashSearch(BaseSearchAlgorithmTest, unittest.TestCase):
    """Concrete test class for HashSearch algorithm"""
    
    def get_search_class(self):
        from src.search.algorithms.hash import HashSearch
        return HashSearch
    
    def get_default_kwargs(self):
        # Remove this since reread_on_query is required as positional arg
        return {}
    
    def get_initial_stat_value(self, stats):
        return stats["hash_time"]
    
    # def get_search_stat_value(self, stats):
    #     return stats["search_time"]
    
    def verify_initial_reread_state(self, search):
        self.assertEqual(len(search._hash_set), 0)
    
    def verify_post_first_search_state(self, search):
        self.assertEqual(len(search._hash_set), 8)
    
    def verify_post_modification_state(self, search):
        self.assertEqual(len(search._hash_set), 9)
    
    def test_search_with_reread(self):
        """Test that file is reread when reread_on_query=True"""
        # Create instance with positional argument
        search = self.get_search_class()(self.test_file, True)
        
        # Initially empty if reread_on_query=True
        self.verify_initial_reread_state(search)
        
        # First search should load data
        self.assertTrue(search.search("banana"))
        self.verify_post_first_search_state(search)
        
        # Modify the file
        with open(self.test_file, 'ab') as f:
            f.write(b"kiwi\n")
        
        # Next search should reload and find new item
        self.assertTrue(search.search("kiwi"))
        self.verify_post_modification_state(search)
    
    def test_hash_search_specific_behavior(self):
        """Test HashSearch specific behavior"""
        hs = self.get_search_class()(self.test_file, reread_on_query=False)
        
        # Test exact matches
        self.assertTrue(hs.search("apple"))
        self.assertTrue(hs.search("banana"))
        self.assertTrue(hs.search("honeydew"))
        
        # Test non-existing items
        self.assertFalse(hs.search("kiwi"))
        self.assertFalse(hs.search("orange"))
        
        # Verify stats
        stats = hs.get_stats()
        self.assertGreater(stats["hash_time"], 0)
        self.assertGreater(stats["search_time"], 0)
    
    def test_case_sensitivity(self):
        """Test that search is case sensitive"""
        hs = self.get_search_class()(self.test_file, reread_on_query=False)
        
        # Different case should not match
        self.assertFalse(hs.search("Apple"))
        self.assertFalse(hs.search("BANANA"))
        
        # Exact case should match
        self.assertTrue(hs.search("apple"))
        self.assertTrue(hs.search("banana"))
    
    def test_empty_string(self):
        """Test behavior with empty string"""
        hs = self.get_search_class()(self.test_file, reread_on_query=False)
        
        # Should not match empty string unless it's in the file
        self.assertFalse(hs.search(""))
        
        # Add empty string to file and test
        empty_file = os.path.join(self.temp_dir.name, "empty_test.txt")
        with open(empty_file, 'wb') as f:
            f.write(b"\n")  # Just a newline
            f.write(b"apple\n")
        
        hs_empty = self.get_search_class()(empty_file, reread_on_query=False)
        self.assertTrue(hs_empty.search(""))  # Empty string should match
    
    def test_duplicate_lines(self):
        """Test behavior with duplicate lines"""
        dup_file = os.path.join(self.temp_dir.name, "duplicates.txt")
        with open(dup_file, 'wb') as f:
            f.write(b"apple\n")
            f.write(b"apple\n")  # Duplicate
            f.write(b"banana\n")
        
        hs = self.get_search_class()(dup_file, reread_on_query=False)
        self.assertEqual(len(hs._hash_set), 2)  # Should only have 2 unique items
        self.assertTrue(hs.search("apple"))
        self.assertTrue(hs.search("banana"))
    
    def test_large_file_performance(self):
        """Test performance with large files"""
        large_file = os.path.join(self.temp_dir.name, "large.txt")
        
        # Create a file with 10,000 unique items
        with open(large_file, 'wb') as f:
            for i in range(10000):
                f.write(f"item_{i}\n".encode('utf-8'))
        
        start_time = time.time()
        hs = self.get_search_class()(large_file, reread_on_query=False)
        load_time = time.time() - start_time
        
        # Verify load time is reasonable
        self.assertLess(load_time, 1.0)  # Should load in under 1 second
        
        # Test search performance
        start_time = time.time()
        self.assertTrue(hs.search("item_0"))
        self.assertTrue(hs.search("item_9999"))
        self.assertFalse(hs.search("item_10000"))
        search_time = time.time() - start_time
        
        # Verify searches are fast
        self.assertLess(search_time, 0.1)  # All searches in under 100ms
        
        # Verify stats
        stats = hs.get_stats()
        self.assertGreater(stats["hash_time"], 0)
        self.assertGreater(stats["search_time"], 0)


class TestRegexSearch(BaseSearchAlgorithmTest, unittest.TestCase):
    """Concrete test class for RegexSearch"""
    
    def get_search_class(self):
        from src.search.algorithms.regex import RegexSearch
        return RegexSearch
    
    def get_default_kwargs(self):
        return {}
    
    # def get_search_stat_value(self, stats):
    #     return stats["search_time"]
    
    def verify_initial_reread_state(self, search):
        self.assertEqual(len(search._lines), 0)
    
    def verify_post_first_search_state(self, search):
        self.assertEqual(len(search._lines), 8)
    
    def verify_post_modification_state(self, search):
        self.assertEqual(len(search._lines), 9)
    
    def test_regex_matching(self):
        """Test RegexSearch specific behavior"""
        search = self.get_search_class()(self.test_file)
        self.assertTrue(search.search(r"^apple$"))
        self.assertFalse(search.search(r"^banana$"))
        self.assertTrue(search.search(r"^.*berry$"))


class TestInMemorySearch(BaseSearchAlgorithmTest, unittest.TestCase):
    """Concrete test class for InMemorySearch"""
    
    def get_search_class(self):
        from src.search.algorithms.inmemory import InMemorySearch
        return InMemorySearch
    
    def get_default_kwargs(self):
        return {}
    
    # def get_search_stat_value(self, stats):
    #     return stats["search_time"]
    
    def verify_initial_reread_state(self, search):
        self.assertEqual(len(search._lines), 0)
    
    def verify_post_first_search_state(self, search):
        self.assertEqual(len(search._lines), 8)
    
    def verify_post_modification_state(self, search):
        self.assertEqual(len(search._lines), 9)
    
    def test_inmemory_search(self):
        """Test InMemorySearch behavior"""
        search = self.get_search_class()(self.test_file)
        self.assertTrue(search.search("apple"))
        self.assertFalse(search.search("kiwi"))


class TestKMP(BaseSearchAlgorithmTest, unittest.TestCase):
    """Concrete test class for KMP (Knuth-Morris-Pratt) search algorithm"""
    
    def get_search_class(self):
        from src.search.algorithms.kmp import KMP
        return KMP
    
    def get_default_kwargs(self):
        return {}
    
    def get_initial_stat_value(self, stats):
        return stats["lines_processed"]
    
    # def get_search_stat_value(self, stats):
    #     return stats["search_time"]
    
    def verify_initial_reread_state(self, search):
        self.assertEqual(len(search._lines), 0)
    
    def verify_post_modification_state(self, search):
        self.assertEqual(len(search._lines), 10)  # 8 original + 1 new + 1 empty from trailing \n

    def verify_post_first_search_state(self, search):
        self.assertEqual(len(search._lines), 9)
    
    def test_search_with_reread(self):
        """Test that file is reread when reread_on_query=True"""
        # Create instance with positional argument
        search = self.get_search_class()(self.test_file, True)
        
        # Initially empty if reread_on_query=True
        self.verify_initial_reread_state(search)
        
        # First search should load data
        self.assertTrue(search.search("banana"))
        self.verify_post_first_search_state(search)
        
        # Modify the file
        with open(self.test_file, 'ab') as f:
            f.write(b"kiwi\n")
        
        # Next search should reload and find new item
        self.assertTrue(search.search("kiwi"))
        self.verify_post_modification_state(search)
    
    def test_kmp_specific_behavior(self):
        """Test KMP-specific pattern matching behavior"""
        search = self.get_search_class()(self.test_file)
        
        # Test exact matches
        self.assertTrue(search.search("apple"))
        self.assertTrue(search.search("banana"))
        
        # Test non-existing items
        self.assertFalse(search.search("kiwi"))
        self.assertFalse(search.search("orange"))
        
        # Verify stats
        stats = search.get_stats()
        self.assertGreater(stats["comparisons"], 0)
        self.assertGreater(stats["search_time"], 0)
    
    def test_partial_matches(self):
        """Test behavior with partial matches"""
        partial_file = os.path.join(self.temp_dir.name, "partial.txt")
        with open(partial_file, 'w', encoding='utf-8') as f:
            f.write("PARTIAL_MATCH_TEST\nTHIS_IS_A_TEST\nTESTING_PARTIAL_MATCHES")
        
        kmp = self.get_search_class()(partial_file)
        self.assertEqual(len(kmp._lines), 3)
        self.assertFalse(kmp.search("PARTIAL"))
        self.assertFalse(kmp.search("TEST"))
        self.assertTrue(kmp.search("THIS_IS_A_TEST"))
        self.assertTrue(kmp.search("TESTING_PARTIAL_MATCHES"))


class TestRabinKarp(BaseSearchAlgorithmTest, unittest.TestCase):
    """Concrete test class for Rabin-Karp search algorithm"""
    
    def get_search_class(self):
        from src.search.algorithms.rabinkarp import RabinKarp
        return RabinKarp
    
    def get_default_kwargs(self):
        return {}
    
    def verify_initial_reread_state(self, search):
        self.assertEqual(len(search._lines), 0)
    
    def verify_post_first_search_state(self, search):
        self.assertEqual(len(search._lines), 8)
    
    def verify_post_modification_state(self, search):
        self.assertEqual(len(search._lines), 9)
    
    def test_rabin_karp_specific_behavior(self):
        """Test Rabin-Karp specific behavior"""
        search = self.get_search_class()(self.test_file)
        
        # Test exact matches
        self.assertTrue(search.search("apple"))
        self.assertTrue(search.search("banana"))
        
        # Test non-existing items
        self.assertFalse(search.search("kiwi"))
        self.assertFalse(search.search("orange"))
        
    
    def test_large_file_performance(self):
        """Test performance with large files"""
        large_file = os.path.join(self.temp_dir.name, "large.txt")
        
        # Create a file with 10,000 unique items
        with open(large_file, 'wb') as f:
            for i in range(10000):
                f.write(f"item_{i}\n".encode('utf-8'))
        
        start_time = time.time()
        rk = self.get_search_class()(large_file)
        load_time = time.time() - start_time
        
        # Verify load time is reasonable
        self.assertLess(load_time, 1.0)  # Should load in under 1 second
        
        # Test search performance
        start_time = time.time()
        self.assertTrue(rk.search("item_0"))
        self.assertTrue(rk.search("item_9999"))
        self.assertFalse(rk.search("item_10000"))
        search_time = time.time() - start_time
        
        # Verify searches are fast
        self.assertLess(search_time, 0.1)  # All searches in under 100ms


    def get_search_class(self):
        from src.search.algorithms.binary import BinarySearch
        return BinarySearch
    
    def get_default_kwargs(self):
        return {}
    
    def get_initial_stat_value(self, stats):
        return stats["time_taken"]
    
    def get_search_stat_value(self, stats):
        return stats["time_taken"]
    
    def verify_initial_reread_state(self, search):
        self.assertEqual(len(search._sorted_lines), 0)
    
    def verify_post_first_search_state(self, search):
        self.assertEqual(len(search._sorted_lines), 8)
    
    def verify_post_modification_state(self, search):
        self.assertEqual(len(search._sorted_lines), 9)
    
    def test_search_comparisons(self):
        """BinarySearch specific test for comparison counting"""
        search = self.get_search_class()(self.test_file)
        search.search("date")
        stats = search.get_stats()
        self.assertGreater(stats["comparisons"], 0)
        self.assertLess(stats["comparisons"], 4)  # log2(8) = 3 max


if __name__ == '__main__':
    pytest.main()