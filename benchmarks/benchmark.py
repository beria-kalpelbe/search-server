import os
import time
import random
import string
from typing import List, Type, Dict
import pandas as pd
import matplotlib.pyplot as plt
from src.search.base import SearchAlgorithm
from src.search.algorithms.simple import SimpleSearch
from src.search.algorithms.inmemory import InMemorySearch
from src.search.algorithms.binary import BinarySearch
from src.search.algorithms.hash import HashSearch
from src.search.algorithms.regex import RegexSearch
from src.search.algorithms.bloomfilter import BloomFilterSearch
from src.search.algorithms.boyermoore import BoyerMoore
from src.search.algorithms.rabinkarp import RabinKarp
from src.search.algorithms.kmp import KMP
from src.client.client import SearchClient


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
    
    def run_benchmark(self, file_sizes: List[int], queries: List[str], reread: bool = False) -> None:
        self.results.clear()        
        for size in file_sizes:
            filename = f"test_{size}.txt"
            filepath = self.generate_test_file(size, filename)
            for algo_name, algo_class in self.algorithms.items():
                if algo_name not in self.results:
                    self.results[algo_name] = []                
                algo = algo_class(filepath, reread_on_query=reread)
                total_search_time = 0
                for query in queries:
                    if reread and hasattr(algo, '_cache'):
                        algo._cache = None                    
                    search_start = time.time()
                    matched = algo.search(query)
                    search_time = time.time() - search_start
                    total_search_time += search_time
                stats = algo.get_stats()
                stats.update({
                    "file_size": size,
                    "avg_search_time": 1000 * total_search_time / len(queries),
                })
                self.results[algo_name].append(stats)
                algo.cleanup()
    
    def generate_report(self) -> None:
        data = []
        for algo_name, results in self.results.items():
            for result in results:
                result["algorithm"] = algo_name
                data.append(result)
        df = pd.DataFrame(data)
        
        plt.figure(figsize=(15, 10))        
        # plt.subplot(1, 2, 2)
        for algo in df["algorithm"].unique():
            algo_data = df[df["algorithm"] == algo]
            plt.plot(algo_data["file_size"], algo_data["avg_search_time"], marker='o', label=algo)
        # plt.xscale('log')
        plt.yscale('log')
        plt.xlabel("File Size (lines) [Log Scale]")
        plt.ylabel("Average Search Time (ms)")
        plt.title("Search Time vs File Size")
        plt.legend()
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "benchmark_results.png"))
        
        df.to_csv(os.path.join(self.output_dir, "benchmark_results.csv"), index=False)
        
        with open(os.path.join(self.output_dir, "benchmark_report.txt"), 'w') as f:
            f.write("Benchmark Summary\n")
            f.write("================\n\n")
            for algo in df["algorithm"].unique():
                algo_data = df[df["algorithm"] == algo]
                f.write(f"\n{algo} Algorithm:\n")
                f.write("-" * (len(algo) + 11) + "\n")
                f.write(f"Average search time: {algo_data['avg_search_time'].mean():.4f}ms\n")
                f.write("\n") 