import os
import sys
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmarks.benchmark import Benchmark

def main():
    parser = argparse.ArgumentParser(description="Run search algorithm benchmarks")
    parser.add_argument("--sizes", type=int, nargs="+", default=list(range(10_000, 1_000_001, 50_000)),
                      help="File sizes to test (from 10 to 10^6 with step 50)")
    parser.add_argument("--output-dir", default="benchmark_results",
                      help="Directory for benchmark results")
    parser.add_argument("--reread", action="store_true",
                      help="Reread the file for each query (default: False)")
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
    print(f"File sizes: {len(args.sizes)}")
    print(f"Number of queries: {len(queries)}")
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