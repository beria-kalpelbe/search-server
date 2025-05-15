"""Benchmark framework for search algorithms."""

import os
import time
import random
import string
from typing import List, Type, Dict
import pandas as pd
import matplotlib.pyplot as plt
from src.search.base import SearchAlgorithm
from src.search.algorithms import (
    SimpleSearch,
    InMemorySearch,
    BinarySearch,
    HashSearch,
    RegexSearch,
    BloomFilterSearch
)

class Benchmark:
    """Benchmark framework for search algorithms."""
    
    def __init__(self, output_dir: str = "benchmark_results"):
        self.output_dir = output_dir
        self.algorithms = {
            "Simple": SimpleSearch,
            "InMemory": InMemorySearch,
            "Binary": BinarySearch,
            "Hash": HashSearch,
            "Regex": RegexSearch,
            "BloomFilter": BloomFilterSearch
        }
        self.results: Dict[str, List[Dict]] = {}
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_test_file(self, size: int, filename: str) -> str:
        """Generate a test file with random content.
        
        Args:
            size: Number of lines
            filename: Output filename
            
        Returns:
            Path to generated file
        """
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w') as f:
            for _ in range(size):
                # Generate random line of text
                line_length = random.randint(20, 100)
                line = ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=line_length))
                f.write(line + '\n')
        
        return filepath
    
    def run_benchmark(self, file_sizes: List[int], queries: List[str], reread: bool = False) -> None:
        """Run benchmarks for all algorithms.
        
        Args:
            file_sizes: List of file sizes to test
            queries: List of search queries
            reread: Whether to reread file for each query
        """
        self.results.clear()
        
        for size in file_sizes:
            filename = f"test_{size}.txt"
            filepath = self.generate_test_file(size, filename)
            
            for algo_name, algo_class in self.algorithms.items():
                if algo_name not in self.results:
                    self.results[algo_name] = []
                
                # Initialize algorithm
                algo = algo_class(filepath)
                
                # Prepare (build index, etc.)
                prep_start = time.time()
                algo.prepare()
                prep_time = time.time() - prep_start
                
                # Run searches
                total_search_time = 0
                total_matches = 0
                
                for query in queries:
                    if reread and hasattr(algo, '_cache'):
                        algo._cache = None
                    
                    search_start = time.time()
                    matches = list(algo.search(query))
                    search_time = time.time() - search_start
                    
                    total_search_time += search_time
                    total_matches += len(matches)
                
                # Collect results
                stats = algo.get_stats()
                stats.update({
                    "file_size": size,
                    "prep_time": prep_time,
                    "avg_search_time": total_search_time / len(queries),
                    "total_matches": total_matches,
                })
                self.results[algo_name].append(stats)
                
                # Cleanup
                algo.cleanup()
    
    def generate_report(self) -> None:
        """Generate benchmark report with charts."""
        # Convert results to DataFrame
        data = []
        for algo_name, results in self.results.items():
            for result in results:
                result["algorithm"] = algo_name
                data.append(result)
        
        df = pd.DataFrame(data)
        
        # Generate charts
        plt.figure(figsize=(15, 10))
        
        # Preparation time vs file size
        plt.subplot(2, 2, 1)
        for algo in df["algorithm"].unique():
            algo_data = df[df["algorithm"] == algo]
            plt.plot(algo_data["file_size"], algo_data["prep_time"], marker='o', label=algo)
        plt.xlabel("File Size (lines)")
        plt.ylabel("Preparation Time (s)")
        plt.title("Preparation Time vs File Size")
        plt.legend()
        
        # Search time vs file size
        plt.subplot(2, 2, 2)
        for algo in df["algorithm"].unique():
            algo_data = df[df["algorithm"] == algo]
            plt.plot(algo_data["file_size"], algo_data["avg_search_time"], marker='o', label=algo)
        plt.xlabel("File Size (lines)")
        plt.ylabel("Average Search Time (s)")
        plt.title("Search Time vs File Size")
        plt.legend()
        
        # Total matches vs file size
        plt.subplot(2, 2, 3)
        for algo in df["algorithm"].unique():
            algo_data = df[df["algorithm"] == algo]
            plt.plot(algo_data["file_size"], algo_data["total_matches"], marker='o', label=algo)
        plt.xlabel("File Size (lines)")
        plt.ylabel("Total Matches")
        plt.title("Total Matches vs File Size")
        plt.legend()
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "benchmark_results.png"))
        
        # Save detailed results
        df.to_csv(os.path.join(self.output_dir, "benchmark_results.csv"), index=False)
        
        # Generate summary report
        with open(os.path.join(self.output_dir, "benchmark_report.txt"), 'w') as f:
            f.write("Benchmark Summary\n")
            f.write("================\n\n")
            
            for algo in df["algorithm"].unique():
                algo_data = df[df["algorithm"] == algo]
                f.write(f"\n{algo} Algorithm:\n")
                f.write("-" * (len(algo) + 11) + "\n")
                f.write(f"Average preparation time: {algo_data['prep_time'].mean():.4f}s\n")
                f.write(f"Average search time: {algo_data['avg_search_time'].mean():.4f}s\n")
                f.write(f"Total matches found: {algo_data['total_matches'].sum()}\n")
                f.write("\n") 