import os
import sys
import argparse
from typing import List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.search.algorithms.simple import SimpleSearch
from src.search.algorithms.inmemory import InMemorySearch
from src.search.algorithms.binary import BinarySearch
from src.search.algorithms.hash import HashSearch
from src.search.algorithms.regex import RegexSearch
from src.search.algorithms.bloomfilter import BloomFilterSearch
from src.search.algorithms.boyermoore import BoyerMoore
from src.search.algorithms.rabinkarp import RabinKarp
from src.search.algorithms.kmp import KMP
from benchmarks.benchmark import Benchmark

def main():
    parser = argparse.ArgumentParser(description="Run search algorithm benchmarks")
    parser.add_argument("--sizes", type=int, nargs="+", default=[10000, 100000, 1000000],
                      help="File sizes to test")
    parser.add_argument("--output-dir", default="benchmark_results",
                      help="Directory for benchmark results")
    parser.add_argument("--reread", action="store_true",
                      help="Test with REREAD_ON_QUERY=True")
    args = parser.parse_args()
    
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
    
    benchmark = Benchmark(args.output_dir)
    
    print("Running benchmarks...")
    print("===================")
    print(f"File sizes: {args.sizes}")
    print(f"Number of queries: {len(queries)}")
    print(f"REREAD_ON_QUERY: {args.reread}")
    print()
    
    benchmark.run_benchmark(
        file_sizes=args.sizes,
        queries=queries,
        reread=args.reread
    )
    
    print("\nGenerating reports...")
    benchmark.generate_report()
    
    print(f"\nBenchmark results saved to {args.output_dir}")
    print("Files generated:")
    print(f"- {args.output_dir}/benchmark_results.png")
    print(f"- {args.output_dir}/benchmark_results.csv")
    print(f"- {args.output_dir}/benchmark_report.txt")

if __name__ == "__main__":
    main() 