from setuptools import setup, find_packages

setup(
    name="search_server",
    version="0.1.0",
    description="Search server with multiple algorithm implementations",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "cryptography>=42.0.0",
    ],
    entry_points={
        "console_scripts": [
            "search-server=src.server.server:run_server",
        ],
    },
) 