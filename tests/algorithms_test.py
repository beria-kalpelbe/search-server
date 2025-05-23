import pytest
import os
import time
import tempfile

@pytest.fixture
def test_data_file():
    temp_dir = tempfile.TemporaryDirectory()
    test_file = os.path.join(temp_dir.name, "test_data.txt")
    
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
    
    if os.path.exists(test_file):
        os.remove(test_file)
    
    with open(test_file, 'wb') as f:
        for item in test_data:
            f.write(f"{item}\n".encode('utf-8'))
    
    yield test_file, temp_dir.name
    
    temp_dir.cleanup()

@pytest.fixture(params=[
    "binary",
    "bloomfilter",
    "boyermoore",
    "hash",
    "regex",
    "inmemory",
    "kmp",
    "rabinkarp",
    "grep"
])
def search_algo_info(request):
    """Fixture that provides algorithm class, default kwargs, and validation functions"""
    param = request.param
    
    if param == "binary":
        from src.search.algorithms.binary import BinarySearch
        
        def verify_initial_reread_state(search):
            assert len(search._sorted_lines) == 0
        
        def verify_post_first_search_state(search):
            assert len(search._sorted_lines) == 8
        
        def verify_post_modification_state(search):
            assert len(search._sorted_lines) == 9
        
        return {
            "class": BinarySearch,
            "kwargs": {},
            
            "verify_initial_reread_state": verify_initial_reread_state,
            "verify_post_first_search_state": verify_post_first_search_state,
            "verify_post_modification_state": verify_post_modification_state
        }
    
    elif param == "bloomfilter":
        from src.search.algorithms.bloomfilter import BloomFilterSearch
        
        def verify_initial_reread_state(search):
            assert len(search._lines) == 0
        
        def verify_post_first_search_state(search):
            assert len(search._lines) == 8
            pass
        
        def verify_post_modification_state(search):
            assert len(search._lines) == 9
            pass
        
        return {
            "class": BloomFilterSearch,
            "kwargs": {"capacity": 1000000, "error_rate": 0.001},
            
            "verify_initial_reread_state": verify_initial_reread_state,
            "verify_post_first_search_state": verify_post_first_search_state,
            "verify_post_modification_state": verify_post_modification_state
        }
    
    elif param == "boyermoore":
        from src.search.algorithms.boyermoore import BoyerMoore
        
        def verify_initial_reread_state(search):
            assert len(search._lines) == 0
        
        def verify_post_first_search_state(search):
            assert len(search._lines) == 8
        
        def verify_post_modification_state(search):
            assert len(search._lines) == 9
        
        return {
            "class": BoyerMoore,
            "kwargs": {},
            
            "verify_initial_reread_state": verify_initial_reread_state,
            "verify_post_first_search_state": verify_post_first_search_state,
            "verify_post_modification_state": verify_post_modification_state
        }
    
    elif param == "hash":
        from src.search.algorithms.hash import HashSearch
        
        def verify_initial_reread_state(search):
            assert len(search._hash_set) == 0
        
        def verify_post_first_search_state(search):
            assert len(search._hash_set) == 8
        
        def verify_post_modification_state(search):
            assert len(search._hash_set) == 9
        
        return {
            "class": HashSearch,
            "kwargs": {},
            
            "verify_initial_reread_state": verify_initial_reread_state,
            "verify_post_first_search_state": verify_post_first_search_state,
            "verify_post_modification_state": verify_post_modification_state
        }
    
    elif param == "regex":
        from src.search.algorithms.regex import RegexSearch
        
        def verify_initial_reread_state(search):
            assert len(search._lines) == 0
        
        def verify_post_first_search_state(search):
            assert len(search._lines) == 8
        
        def verify_post_modification_state(search):
            assert len(search._lines) == 9
        
        return {
            "class": RegexSearch,
            "kwargs": {},
            
            "verify_initial_reread_state": verify_initial_reread_state,
            "verify_post_first_search_state": verify_post_first_search_state,
            "verify_post_modification_state": verify_post_modification_state
        }
    
    elif param == "inmemory":
        from src.search.algorithms.inmemory import InMemorySearch
        
        def verify_initial_reread_state(search):
            assert len(search._lines) == 0
        
        def verify_post_first_search_state(search):
            assert len(search._lines) == 8
        
        def verify_post_modification_state(search):
            assert len(search._lines) == 9
        
        return {
            "class": InMemorySearch,
            "kwargs": {},
            
            "verify_initial_reread_state": verify_initial_reread_state,
            "verify_post_first_search_state": verify_post_first_search_state,
            "verify_post_modification_state": verify_post_modification_state
        }
    
    elif param == "kmp":
        from src.search.algorithms.kmp import KMP
        
        def verify_initial_reread_state(search):
            assert len(search._lines) == 0
        
        def verify_post_first_search_state(search):
            assert len(search._lines) == 8
        
        def verify_post_modification_state(search):
            assert len(search._lines) == 9
        
        return {
            "class": KMP,
            "kwargs": {},
            
            "verify_initial_reread_state": verify_initial_reread_state,
            "verify_post_first_search_state": verify_post_first_search_state,
            "verify_post_modification_state": verify_post_modification_state
        }
    
    elif param == "rabinkarp":
        from src.search.algorithms.rabinkarp import RabinKarp
        
        def verify_initial_reread_state(search):
            assert len(search._lines) == 0
        
        def verify_post_first_search_state(search):
            assert len(search._lines) == 8
        
        def verify_post_modification_state(search):
            assert len(search._lines) == 9
        
        return {
            "class": RabinKarp,
            "kwargs": {},
            
            "verify_initial_reread_state": verify_initial_reread_state,
            "verify_post_first_search_state": verify_post_first_search_state,
            "verify_post_modification_state": verify_post_modification_state
        }
    elif param == 'grep':
        from src.search.algorithms.grep import GrepSearch
        
        def verify_initial_reread_state(search):
            # assert len(search._lines) == 0
            pass
        
        def verify_post_first_search_state(search):
            # assert len(search._lines) == 8
            pass
        
        def verify_post_modification_state(search):
            # assert len(search._lines) == 9
            pass
        
        return {
            "class": GrepSearch,
            "kwargs": {},
            
            "verify_initial_reread_state": verify_initial_reread_state,
            "verify_post_first_search_state": verify_post_first_search_state,
            "verify_post_modification_state": verify_post_modification_state
        }


def test_init_with_default_parameters(test_data_file, search_algo_info):
    """Test initialization with default parameters"""
    test_file, _ = test_data_file
    search_class = search_algo_info["class"]
    kwargs = search_algo_info["kwargs"]
    
    search = search_class(test_file, **kwargs)
    assert search.reread_on_query is False


def test_search_existing_items(test_data_file, search_algo_info):
    """Test searching for items that exist"""
    test_file, _ = test_data_file
    search_class = search_algo_info["class"]
    kwargs = search_algo_info["kwargs"]
    
    search = search_class(test_file, **kwargs)
    
    assert search.search("apple") is True
    assert search.search("banana") is True
    assert search.search("honeydew") is True


def test_search_non_existing_items(test_data_file, search_algo_info):
    """Test searching for items that don't exist"""
    test_file, _ = test_data_file
    search_class = search_algo_info["class"]
    kwargs = search_algo_info["kwargs"]
    
    search = search_class(test_file, **kwargs)
    
    assert search.search("kiwi") is False
    assert search.search("orange") is False
    assert search.search("watermelon") is False


def test_search_with_reread(test_data_file, search_algo_info):
    """Test that file is reread when reread_on_query=True"""
    test_file, _ = test_data_file
    search_class = search_algo_info["class"]
    verify_initial = search_algo_info["verify_initial_reread_state"]
    verify_first = search_algo_info["verify_post_first_search_state"]
    verify_modification = search_algo_info["verify_post_modification_state"]
    
    search = search_class(test_file, reread_on_query=True)
    
    verify_initial(search)
    
    assert search.search("banana") is True
    verify_first(search)
    
    # Write new data and ensure it's flushed to disk
    with open(test_file, 'ab') as f:
        f.write(b"kiwi\n")
        f.flush()  # Force write to OS buffer
        os.fsync(f.fileno())  # Force OS to write to disk
    
    # Small delay to ensure file system consistency
    time.sleep(0.01)
    assert search.search("kiwi") is True
    verify_modification(search)


def test_empty_file(test_data_file, search_algo_info):
    """Test behavior with empty file"""
    _, temp_dir = test_data_file
    search_class = search_algo_info["class"]
    kwargs = search_algo_info["kwargs"]
    
    empty_file = os.path.join(temp_dir, "empty.txt")
    with open(empty_file, 'wb') as f:
        pass
    
    search = search_class(empty_file, **kwargs)
    assert search.search("anything") is False


def test_case_sensitivity(test_data_file, search_algo_info):
    """Test that search is case sensitive"""
    test_file, _ = test_data_file
    search_class = search_algo_info["class"]
    kwargs = search_algo_info["kwargs"]
    
    search_case_sensitive = search_class(test_file, case_sensitive = True, **kwargs)
    
    assert search_case_sensitive.search("Apple") is False
    assert search_case_sensitive.search("BANANA") is False
    
    assert search_case_sensitive.search("apple") is True
    assert search_case_sensitive.search("banana") is True
    
    search_no_case_sensitive = search_class(test_file, case_sensitive = False, **kwargs)
    
    assert search_no_case_sensitive.search("Apple") is True
    assert search_no_case_sensitive.search("BANANA") is True
    
    assert search_no_case_sensitive.search("apple") is True
    assert search_no_case_sensitive.search("banana") is True


class TestBinarySearch:
    def test_search_comparisons(self, test_data_file):
        """BinarySearch specific test for comparison counting"""
        test_file, _ = test_data_file
        from src.search.algorithms.binary import BinarySearch
        
        search = BinarySearch(test_file)
        search.search("date")


class TestBloomFilterSearch:
    def test_false_positives(self, test_data_file):
        """BloomFilter specific test for false positives"""
        _, temp_dir = test_data_file
        from src.search.algorithms.bloomfilter import BloomFilterSearch
        
        large_file = os.path.join(temp_dir, "large.txt")
        with open(large_file, 'wb') as f:
            for i in range(10000):
                f.write(f"word_{i}\n".encode('utf-8'))
        
        search = BloomFilterSearch(large_file, error_rate=0.01)
        
        false_positives = 0
        tests = 1000
        for i in range(10000, 10000 + tests):
            if search.search(f"word_{i}"):
                false_positives += 1
        
        false_positive_rate = false_positives / tests
        assert false_positive_rate < 0.02


class TestBoyerMoore:
    def test_boyer_moore_specific_behavior(self, test_data_file):
        """Test Boyer-Moore specific pattern matching behavior"""
        _, temp_dir = test_data_file
        from src.search.algorithms.boyermoore import BoyerMoore
        
        pattern_file = os.path.join(temp_dir, "pattern_test.txt")
        with open(pattern_file, 'w', encoding='utf-8') as f:
            f.write("ABACADABRAC\nTESTTESTTEST\nMISSISSIPPI\nABCDEFGHIJKL")
        
        bm = BoyerMoore(pattern_file)
        
        assert len(bm._lines) == 4
        
        assert bm.search("ABACADABRAC") is True
        assert bm.search("TESTTESTTEST") is True
        assert bm.search("MISSISSIPPI") is True
        
        assert bm.search("ABACADABRA") is False
        assert bm.search("ABACADABRACD") is False
        assert bm.search("TESTTESTTES") is False
        
    
    def test_bad_char_table(self, test_data_file):
        """Test the bad character table construction"""
        test_file, _ = test_data_file
        from src.search.algorithms.boyermoore import BoyerMoore
        
        bm = BoyerMoore(test_file)
        table = bm._build_bad_char_table("ABCDABD")
        expected = {
            'A': 2,
            'B': 1,
            'C': 4,
            'D': 3
        }
        assert table == expected
    
    def test_good_suffix_table(self, test_data_file):
        """Test the good suffix table construction"""
        test_file, _ = test_data_file
        from src.search.algorithms.boyermoore import BoyerMoore
        
        bm = BoyerMoore(test_file)
        table = bm._build_good_suffix_table("ABABCBAB")
        assert len(table) == 8
        assert table[0] > 0
    
    def test_is_prefix(self, test_data_file):
        """Test the prefix detection helper"""
        test_file, _ = test_data_file
        from src.search.algorithms.boyermoore import BoyerMoore
        
        bm = BoyerMoore(test_file)
        assert bm._is_prefix("TESTTEST", 4) is True
        assert bm._is_prefix("TESTTEST", 5) is False
        assert bm._is_prefix("ABCABC", 3) is True
    
    def test_find_suffix_length(self, test_data_file):
        """Test the suffix length helper"""
        test_file, _ = test_data_file
        from src.search.algorithms.boyermoore import BoyerMoore
        
        bm = BoyerMoore(test_file)
        assert bm._find_suffix_length("ABCABC", 2) == 3
        assert bm._find_suffix_length("ABCDEF", 2) == 0
        assert bm._find_suffix_length("ABABAB", 4) == 0
    
    def test_partial_matches(self, test_data_file):
        """Test behavior with partial matches"""
        _, temp_dir = test_data_file
        from src.search.algorithms.boyermoore import BoyerMoore
        
        partial_file = os.path.join(temp_dir, "partial.txt")
        with open(partial_file, 'w', encoding='utf-8') as f:
            f.write("PARTIAL_MATCH_TEST\nTHIS_IS_A_TEST\nTESTING_PARTIAL_MATCHES")
        
        bm = BoyerMoore(partial_file)
        assert len(bm._lines) == 3
        assert bm.search("PARTIAL") is False
        assert bm.search("TEST") is False
        assert bm.search("THIS_IS_A_TEST") is True
        assert bm.search("TESTING_PARTIAL_MATCHES") is True


class TestHashSearch:
    def test_hash_search_specific_behavior(self, test_data_file):
        """Test HashSearch specific behavior"""
        test_file, _ = test_data_file
        from src.search.algorithms.hash import HashSearch
        
        hs = HashSearch(test_file, reread_on_query=False)
        
        assert hs.search("apple") is True
        assert hs.search("banana") is True
        assert hs.search("honeydew") is True
        
        assert hs.search("kiwi") is False
        assert hs.search("orange") is False
        
    def test_empty_string(self, test_data_file):
        """Test behavior with empty string"""
        test_file, temp_dir = test_data_file
        from src.search.algorithms.hash import HashSearch
        
        hs = HashSearch(test_file, reread_on_query=False)
        
        assert hs.search("") is False
        
        empty_file = os.path.join(temp_dir, "empty_test.txt")
        with open(empty_file, 'wb') as f:
            f.write(b"\n")
            f.write(b"apple\n")
        
        hs_empty = HashSearch(empty_file, reread_on_query=False)
        assert hs_empty.search("") is True
    
    def test_duplicate_lines(self, test_data_file):
        """Test behavior with duplicate lines"""
        _, temp_dir = test_data_file
        from src.search.algorithms.hash import HashSearch
        
        dup_file = os.path.join(temp_dir, "duplicates.txt")
        with open(dup_file, 'wb') as f:
            f.write(b"apple\n")
            f.write(b"apple\n")
            f.write(b"banana\n")
        
        hs = HashSearch(dup_file, reread_on_query=False)
        assert len(hs._hash_set) == 2
        assert hs.search("apple") is True
        assert hs.search("banana") is True
    
    def test_large_file_performance(self, test_data_file):
        """Test performance with large files"""
        _, temp_dir = test_data_file
        from src.search.algorithms.hash import HashSearch
        
        large_file = os.path.join(temp_dir, "large.txt")

        def test_regex_search_initial_state(test_data_file):
            """Test initial state of RegexSearch"""
            test_file, _ = test_data_file
            from src.search.algorithms.regex import RegexSearch
            
            search = RegexSearch(test_file)
            assert hasattr(search, '_lines'), "RegexSearch object should have a '_lines' attribute"
            assert len(search._lines) == 0, "Initial '_lines' should be empty"

        def test_regex_search_post_search_state(test_data_file):
            """Test state of RegexSearch after performing a search"""
            test_file, _ = test_data_file
            from src.search.algorithms.regex import RegexSearch
            
            search = RegexSearch(test_file)
            search.search(r"^apple$")
            assert len(search._lines) == 8, "After first search, '_lines' should contain all lines from the file"

        def test_rabinkarp_search_modification(test_data_file):
            """Test Rabin-Karp search behavior after file modification"""
            test_file, _ = test_data_file
            from src.search.algorithms.rabinkarp import RabinKarp
            
            search = RabinKarp(test_file)
            assert len(search._lines) == 8, "Initial '_lines' should contain all lines from the file"
            
            with open(test_file, 'ab') as f:
                f.write(b"kiwi\n")
            
            search.search("kiwi")
            assert len(search._lines) == 9, "After modification, '_lines' should contain the new line"

        def test_regex_search_matching_behavior(test_data_file):
            """Test RegexSearch matching behavior with corrected assertions"""
            test_file, _ = test_data_file
            from src.search.algorithms.regex import RegexSearch
            
            search = RegexSearch(test_file)
            assert search.search(r"^apple$") is True, "Exact match for 'apple' should return True"
            assert search.search(r"^banana$") is True, "Exact match for 'banana' should return True"
            assert search.search(r"^.*berry$") is True, "Pattern matching '.*berry' should return True"


class TestInMemorySearch:
    def test_inmemory_search(self, test_data_file):
        """Test InMemorySearch behavior"""
        test_file, _ = test_data_file
        from src.search.algorithms.inmemory import InMemorySearch
        
        search = InMemorySearch(test_file)
        assert search.search("apple") is True
        assert search.search("kiwi") is False


class TestKMP:
    def test_kmp_specific_behavior(self, test_data_file):
        """Test KMP-specific pattern matching behavior"""
        test_file, _ = test_data_file
        from src.search.algorithms.kmp import KMP
        
        search = KMP(test_file)
        
        assert search.search("apple") is True
        assert search.search("banana") is True
        
        assert search.search("kiwi") is False
        assert search.search("orange") is False

    
    def test_partial_matches(self, test_data_file):
        """Test behavior with partial matches"""
        _, temp_dir = test_data_file
        from src.search.algorithms.kmp import KMP
        
        partial_file = os.path.join(temp_dir, "partial.txt")
        with open(partial_file, 'w', encoding='utf-8') as f:
            f.write("PARTIAL_MATCH_TEST\nTHIS_IS_A_TEST\nTESTING_PARTIAL_MATCHES")
        
        kmp = KMP(partial_file)
        assert len(kmp._lines) == 3
        assert kmp.search("PARTIAL") is False
        assert kmp.search("TEST") is False
        assert kmp.search("THIS_IS_A_TEST") is True
        assert kmp.search("TESTING_PARTIAL_MATCHES") is True


class TestRabinKarp:
    def test_rabin_karp_specific_behavior(self, test_data_file):
        """Test Rabin-Karp specific behavior"""
        test_file, _ = test_data_file
        from src.search.algorithms.rabinkarp import RabinKarp
        
        search = RabinKarp(test_file)
        
        assert search.search("apple") is True
        assert search.search("banana") is True
        
        assert search.search("kiwi") is False
        assert search.search("orange") is False
    
    def test_large_file_performance(self, test_data_file):
        """Test performance with large files"""
        _, temp_dir = test_data_file
        from src.search.algorithms.rabinkarp import RabinKarp
        
        large_file = os.path.join(temp_dir, "large.txt")
        
        with open(large_file, 'wb') as f:
            for i in range(10000):
                f.write(f"item_{i}\n".encode('utf-8'))
        
        start_time = time.time()
        rk = RabinKarp(large_file)
        load_time = time.time() - start_time
        
        assert load_time < 10.0
        
        start_time = time.time()
        assert rk.search("item_0") is True
        assert rk.search("item_9999") is True
        assert rk.search("item_10000") is False
        search_time = time.time() - start_time
        
        assert search_time < 100