import os
import time
import random
import string
from typing import List, Type, Dict
import pandas as pd
import matplotlib.pyplot as plt
from src.search.algorithms.simple import SimpleSearch
from src.search.algorithms.inmemory import InMemorySearch
from src.search.algorithms.binary import BinarySearch
from src.search.algorithms.hash import HashSearch
from src.search.algorithms.regex import RegexSearch
from src.search.algorithms.bloomfilter import BloomFilterSearch
from src.search.algorithms.boyermoore import BoyerMoore
from src.search.algorithms.rabinkarp import RabinKarp
from src.search.algorithms.kmp import KMP
from src.search.algorithms.grep import GrepSearch
import tracemalloc


class Benchmark:    
    """
    Comprehensive benchmarking suite for search algorithms.

    This class provides tools to:
    1. Generate test data of varying sizes
    2. Measure algorithm performance metrics
    3. Compare different search implementations
    4. Generate detailed reports and visualizations

    Performance metrics tracked:
    - Search time (ms)
    - Memory usage (kB)
    - Throughput (queries/ms)
    - Number of comparisons
    """
    
    def __init__(self, output_dir: str = "benchmark_results"):
        """
        Initialize the benchmark suite.

        Args:
            output_dir (str): Directory for storing benchmark results and reports.
        """
        self.output_dir = output_dir
        self.algorithms = {
            "Simple": SimpleSearch,
            "InMemory": InMemorySearch,
            "Binary": BinarySearch,
            "Hash": HashSearch,
            "Regex": RegexSearch,
            "BloomFilter": BloomFilterSearch,
            "BoyerMoore": BoyerMoore,
            "RabinKarp": RabinKarp,
            "KMP": KMP,
            "GrepSearch": GrepSearch,
        }
        self.results: Dict[str, List[Dict]] = {}
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_test_file(self, size: int, filename: str) -> str:
        """
        Generate a test file with random content.

        Args:
            size (int): Number of lines to generate
            filename (str): Name of the output file

        Returns:
            str: Path to the generated file

        Note:
            Generated lines vary in length from 20 to 100 characters
            using ASCII letters, digits, and spaces.
        """
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w') as f:
            for _ in range(size):
                line_length = random.randint(20, 100)
                line = ''.join(random.choices(
                    string.ascii_letters + string.digits + ' ',
                    k=line_length
                ))
                f.write(line + '\n')
        return filepath

    def measure_memory(self, func, *args) -> float:
        """
        Measure peak memory usage of a function.

        Args:
            func: Function to measure
            *args: Arguments to pass to the function

        Returns:
            float: Peak memory usage in kilobytes
        """
        tracemalloc.start() 
        func(*args)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return peak / 1024
    
    def measure_throughput(self, search_func, queries: List[str], n_runs: int = 10) -> float:
        """
        Measure search throughput.

        Args:
            search_func: Search function to test
            queries: List of search queries
            n_runs: Number of times to repeat the test

        Returns:
            float: Queries processed per millisecond
        """
        start_time = time.perf_counter()
        for _ in range(n_runs):
            for query in queries:
                search_func(query)
        total_time = time.perf_counter() - start_time
        qpms = (len(queries) * n_runs) / (1000 * total_time)
        return qpms
    
    def run_benchmark(self, file_sizes: List[int], queries: List[str], reread: bool = False) -> None:
        """
        Run comprehensive benchmarks across all algorithms.

        Args:
            file_sizes: List of file sizes to test
            queries: List of search queries to use
            reread: Whether to reread file for each query

        This method:
        1. Generates test files of specified sizes
        2. Tests each algorithm with all queries
        3. Measures performance metrics
        4. Stores results for reporting
        """
        self.results.clear()
        total_steps = len(file_sizes) * len(self.algorithms)
        current_step = 0
        
        for size in file_sizes:
            filename = f"bench_{size}.txt"
            filepath = self.generate_test_file(size, filename)
            for algo_name, algo_class in self.algorithms.items():
                current_step += 1
                print(
                    f"Running benchmark: {current_step}/{total_steps} - "
                    f"Algorithm: {algo_name}, File Size: {size} lines",
                    end='\r'
                )
                
                if algo_name not in self.results:
                    self.results[algo_name] = []
                    
                algo = algo_class(filepath, reread_on_query=reread)
                total_search_time = 0
                total_memory_usage = 0
                
                for query in queries:
                    if reread and hasattr(algo, '_cache'):
                        algo._cache = None
                    search_start = time.time()
                    matched = algo.search(query)
                    search_time = time.time() - search_start
                    total_memory_usage += self.measure_memory(algo.search, query)
                    total_search_time += search_time
                    
                stats = {
                    "file_size": size,
                    "avg_search_time": 1000 * total_search_time / len(queries),
                    "memory_usage": total_memory_usage / len(queries),
                    "throughput": self.measure_throughput(algo.search, queries),
                }
                self.results[algo_name].append(stats)
        
        print("\nBenchmark completed.")
    
    def plot_figure(self, data: pd.DataFrame, x: str, y: str, xlabel: str, ylabel: str,
                   title: str, filename: str, log_scale_x: bool = False,
                   log_scale_y: bool = False) -> None:
        """
        Generate a performance visualization plot.

        Args:
            data: DataFrame containing benchmark results
            x: Column name for x-axis
            y: Column name for y-axis
            xlabel: X-axis label
            ylabel: Y-axis label
            title: Plot title
            filename: Output file path
            log_scale_x: Use logarithmic scale for x-axis
            log_scale_y: Use logarithmic scale for y-axis
        """
        plt.figure(figsize=(15, 10))
        df = pd.DataFrame(data)
        for algo in df["algorithm"].unique():
            algo_data = df[df["algorithm"] == algo]
            plt.plot(algo_data[x], algo_data[y], marker='o', label=algo)
            
        if log_scale_x:
            plt.xscale('log')
        if log_scale_y:
            plt.yscale('log')
            
        plt.xlabel(xlabel + " [Log Scale]" if log_scale_x else xlabel)
        plt.ylabel(ylabel + " [Log Scale]" if log_scale_y else ylabel)
        plt.legend()
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()
    
    def generate_report(self) -> None:
        """
        Generate comprehensive benchmark reports.

        Creates:
        1. CSV file with raw benchmark data
        2. Performance visualization plots
        3. Text report with statistical summary
        4. Comparative analysis of algorithms
        """
        data = []
        for algo_name, results in self.results.items():
            for result in results:
                result["algorithm"] = algo_name
                data.append(result)
                
        df = pd.DataFrame(data)
        print(df.head())
        
        # Generate performance plots
        self.plot_figure(
            data=df,
            x="file_size",
            y="avg_search_time",
            xlabel="File Size (lines)",
            ylabel="Average Search Time (ms)",
            title="Search Time vs File Size",
            filename=os.path.join(self.output_dir, "time-speed.png"),
            log_scale_x=False,
            log_scale_y=True
        )
        
        self.plot_figure(
            data=data,
            x="file_size",
            y="memory_usage",
            xlabel="File Size (lines)",
            ylabel="Memory Usage (kB)",
            title="Memory Usage vs File Size",
            filename=os.path.join(self.output_dir, "memory_usage.png"),
            log_scale_y=True
        )
        
        self.plot_figure(
            data=data,
            x="file_size",
            y="throughput",
            xlabel="File Size (lines)",
            ylabel="Throughput (queries/ms)",
            title="Throughput vs File Size",
            filename=os.path.join(self.output_dir, "throughput.png"),
            log_scale_y=True
        )
        
        # Save raw data
        df.to_csv(os.path.join(self.output_dir, "benchmark_results.csv"), index=False)
        
        # Generate summary report
        with open(os.path.join(self.output_dir, "benchmark_report.txt"), 'w') as f:
            f.write("Benchmark Summary\n")
            f.write("==================\n\n")
            f.write(
                f"{'Algorithm':<20}{'Avg Search Time (ms)':<25}"
                f"{'Memory Usage (kB)':<20}{'Throughput (queries/ms)':<25}\n"
            )
            f.write("=" * 90 + "\n")
            
            for algo in df["algorithm"].unique():
                algo_data = df[df["algorithm"] == algo]
                avg_search_time = algo_data['avg_search_time'].mean()
                memory_usage = algo_data['memory_usage'].mean()
                throughput = algo_data['throughput'].mean()
                f.write(
                    f"{algo:<20}{avg_search_time:<25.4f}"
                    f"{memory_usage:<20.4f}{throughput:<25.4f}\n"
                )