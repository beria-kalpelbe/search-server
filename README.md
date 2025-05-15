# Search Server

A simple search server that checks if a string exists in a file. Supports multiple search algorithms and SSL encryption.

## Quick Start

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
echo "some test data" > data/test.txt
```

4. Configure the server (server.conf):
```ini
server.host=localhost
server.port=8443
server.workers=4
server.debug=false

ssl.enabled=true
ssl.cert_file=certs/server.crt
ssl.key_file=certs/server.key

search.algorithm=inmemory
search.data_file=data/test.txt
search.case_sensitive=false
search.max_results=100

logging.level=INFO
logging.file=logs/server.log
```

5. Start the server:
```bash
search-server
```

6. Test with the client:
```bash
python test_client.py
```

## Protocol

The server accepts plain text queries and responds with either:
- "STRING EXISTS" - if the string is found in the file
- "STRING NOT FOUND" - if the string is not found

## Project Structure

```
.
├── algo_science/          # Main package
│   ├── config/           # Configuration handling
│   ├── search/          # Search algorithms
│   └── server/          # Server implementation
├── certs/               # SSL certificates
├── data/                # Search data files
├── server.conf          # Server configuration
└── test_client.py       # Test client
```

## Search Algorithms

- simple: Line-by-line search
- inmemory: Full file in-memory search
- binary: Binary search (for sorted files)
- hash: Hash-based search
- regex: Regular expression search
- bloom: Bloom filter search
