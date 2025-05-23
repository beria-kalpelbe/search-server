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
    def __init__(self, output_dir: str = "benchmark_results"):
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
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w') as f:
            for _ in range(size):
                line_length = random.randint(20, 100)
                line = ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=line_length))
                f.write(line + '\n')
        return filepath

    def measure_memory(self, func, *args):
        tracemalloc.start() 
        func(*args)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return peak / 1024
    
    def measure_throughput(self, search_func, queries, n_runs=10):
        start_time = time.perf_counter()
        for _ in range(n_runs):
            for query in queries:
                search_func(query)
        total_time = time.perf_counter() - start_time
        qpms = (len(queries) * n_runs) / 1000*total_time
        return qpms
    
    def run_benchmark(self, file_sizes: List[int], queries: List[str], reread: bool = False) -> None:
        self.results.clear()
        total_steps = len(file_sizes) * len(self.algorithms)
        current_step = 0
        
        for size in file_sizes:
            filename = f"bench_{size}.txt"
            filepath = self.generate_test_file(size, filename)
            for algo_name, algo_class in self.algorithms.items():
                current_step += 1
                print(f"Running benchmark: {current_step}/{total_steps} - Algorithm: {algo_name}, File Size: {size} lines", end='\r')
                
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
                # algo.cleanup() 
        
        print("\nBenchmark completed.")
    
    def plot_figure(self, data, x, y, xlabel, ylabel, title, filename, log_scale_x=False, log_scale_y=False):
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
            # plt.title(title)
            plt.legend()
            plt.tight_layout()
            plt.savefig(filename)
            plt.close()
    
    def generate_report(self) -> None:
        data = []
        for algo_name, results in self.results.items():
            for result in results:
                result["algorithm"] = algo_name
                data.append(result)
        df = pd.DataFrame(data)
        print(df.head())
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
        
        df.to_csv(os.path.join(self.output_dir, "benchmark_results.csv"), index=False)
        
        with open(os.path.join(self.output_dir, "benchmark_report.txt"), 'w') as f:
            f.write("Benchmark Summary\n")
            f.write("==================\n\n")
            f.write(f"{'Algorithm':<20}{'Avg Search Time (ms)':<25}{'Memory Usage (kB)':<20}{'Throughput (queries/ms)':<25}\n")
            f.write("=" * 90 + "\n")
            for algo in df["algorithm"].unique():
                algo_data = df[df["algorithm"] == algo]
                avg_search_time = algo_data['avg_search_time'].mean()
                memory_usage = algo_data['memory_usage'].mean()
                throughput = algo_data['throughput'].mean()
                f.write(f"{algo:<20}{avg_search_time:<25.4f}{memory_usage:<20.4f}{throughput:<25.4f}\n")