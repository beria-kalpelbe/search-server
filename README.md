# Search Server

A simple search server that checks if a string exists in a file. Supports multiple search algorithms and SSL encryption.

## Quick Start

0. Set up environment for Python 3.12
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

1. Install the package:
```bash
pip install -e .
```

2. Generate SSL certificates (if using SSL):
```bash
mkdir -p certs
openssl req -x509 -newkey rsa:2048 -keyout certs/server.key -out certs/server.crt -days 365 -nodes -subj "/CN=localhost"
```

3. Create a data file to search in:
```bash
mkdir -p data
echo "Existing line" > data/test.txt
```

4. Configure the server (src/config/server.conf):
```ini
[Server]
host = localhost
port = 8443
workers = 4
debug = true
use_ssl = true
ssl_cert = certs/server.crt
ssl_key = certs/server.key

[Search]
algorithm = simple
linux_path = data/200k.txt
case_sensitive = false
max_results = 100
reread_on_query = true

[Logging]
level = INFO
file = logs/server.log 
```

5. Start the server:
```bash
search-server
```

6. Test with a single request
```bash
nc localhost 8443
Existing line
Unexisting line
```

6. Test with the client:
```bash
python src/client/client.py --queries "Existing line" "Unexisting line"
```

## Protocol

The server accepts plain text queries and responds with either:
- "STRING EXISTS" - if the string is found in the file
- "STRING NOT FOUND" - if the string is not found

## Project Structure

```
.
├── benchmarks/          # Benchmarks
├── certs/               # SSL certificates
├── data/                # Search data files
├── scripts/             # Helper scripts
├── src/                 # Main package
|   ├── client/
│   ├── config/          # Configuration handling
│   ├── search/          # Search algorithms
│   └── server/          # Server implementation
└── tests/               # Test folder
```

## Search Algorithms

- simple: Line-by-line search
- inmemory: Full file in-memory search
- binary: Binary search (for sorted files)
- hash: Hash-based search
- regex: Regular expression search
- bloom: Bloom filter search
