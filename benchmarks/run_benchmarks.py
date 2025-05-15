"""Script to run benchmarks for all search algorithms."""

import os
import sys
import argparse
from typing import List

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.search.algorithms import (
    SimpleSearch,
    InMemorySearch,
    BinarySearch,
    HashSearch,
    RegexSearch,
    BloomFilterSearch
)
from benchmarks.benchmark import Benchmark

def main():
    """Run benchmarks with various file sizes and configurations."""
    parser = argparse.ArgumentParser(description="Run search algorithm benchmarks")
    parser.add_argument("--sizes", type=int, nargs="+", default=[10000, 100000, 1000000],
                      help="File sizes to test")
    parser.add_argument("--output-dir", default="benchmark_results",
                      help="Directory for benchmark results")
    parser.add_argument("--reread", action="store_true",
                      help="Test with REREAD_ON_QUERY=True")
    args = parser.parse_args()
    
    # Sample queries for testing
    queries = [
        "example",
        "test data",
        "performance",
        "benchmark",
        "algorithm",
        "search string",
        "nonexistent",
        "quick brown fox",
        "python programming",
        "data structures"
    ]
    
    # Initialize benchmark framework
    benchmark = Benchmark(args.output_dir)
    
    print("Running benchmarks...")
    print("===================")
    print(f"File sizes: {args.sizes}")
    print(f"Number of queries: {len(queries)}")
    print(f"REREAD_ON_QUERY: {args.reread}")
    print()
    
    # Run benchmarks
    benchmark.run_benchmark(
        file_sizes=args.sizes,
        queries=queries,
        reread=args.reread
    )
    
    # Generate report
    print("\nGenerating reports...")
    benchmark.generate_report()
    
    print(f"\nBenchmark results saved to {args.output_dir}")
    print("Files generated:")
    print(f"- {args.output_dir}/benchmark_results.png")
    print(f"- {args.output_dir}/benchmark_results.csv")
    print(f"- {args.output_dir}/benchmark_report.txt")

if __name__ == "__main__":
    main() 