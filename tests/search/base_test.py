import tempfile
import os
from abc import ABC, abstractmethod

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