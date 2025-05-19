# Search Server

A high-performance server that checks if a string exists in a file using multiple search algorithms with SSL encryption support.

![Python](https://img.shields.io/badge/python-3.12-green.svg)

## Features

- **Multiple Search Algorithms**: Choose from 9 different search implementations
- **High Performance**: Optimized for speed with configurable worker threads
- **Secure Communication**: Built-in SSL/TLS support
- **Configurable**: Extensive configuration options
- **Linux Daemon**: Runs as a system service for production deployments

## Quick Start

### Server Installation

1. **Set up Python environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Generate SSL certificates** (optional for secure connections):
   ```bash
   mkdir -p certs
   openssl req -x509 -newkey rsa:2048 -keyout certs/server.key \
     -out certs/server.crt -days 365 -nodes -subj "/CN=localhost"
   ```

3. **Prepare data file**:
   ```bash
   mkdir -p data
   echo "Existing line" > data/test.txt
   ```

4. **Install as system service**:
   ```bash
   chmod +x service/install.sh
   sudo service/install.sh
   ```

5. **Verify installation**:
   ```bash
   systemctl status search-server.service
   ```

### Client Usage

1. **Set up environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Send test queries**:
    Use the client script to send search queries to the server. Below are the available parameters for the command:

    - `--host`: Server hostname (default: `localhost`).
    - `--port`: Server port (default: `8443`).
    - `--no-ssl`: Disable SSL for the connection.
    - `--cert`: Path to the server certificate for SSL verification.
    - `--queries`: List of search queries to send (default: `['test']`).
    - `--threads`: Number of concurrent threads to use (default: `10`).

    Example usage:
    ```bash
    python src/client/client.py --host localhost --port 8443 --queries "Existing line" "Unexisting line"
    ```
    This command sends two queries, `"Existing line"` and `"Unexisting line"`, to the server running on `localhost` at port `8443`. By default, SSL is enabled unless `--no-ssl` is specified.

## Configuration

Edit the server configuration in `src/config/server.conf`:

```ini
[SERVER]
HOST = localhost
PORT = 8443
WORKERS = 100
DEBUG = false
USE_SSL = true
SSL_CERT = certs/server.crt
SSL_KEY = certs/server.key

[SEARCH]
ALGORITHM = regex
LINUX_PATH = data/200k.txt
CASE_SENSITIVE = true
MAX_RESULTS = 100
REREAD_ON_QUERY = true

[LOGGING]
LEVEL = INFO
FILE = logs/server.log
```

## Search Algorithms

| Algorithm    | Description                                         | Best Use Case                      |
|--------------|-----------------------------------------------------|-----------------------------------|
| `simple`     | Line-by-line search                                 | Small files, simple needs          |
| `inmemory`   | Full file in-memory search                          | Speed priority, sufficient RAM     |
| `binary`     | Binary search                                       | Large sorted files                 |
| `hash`       | Hash-based search                                   | Exact string matching              |
| `regex`      | Regular expression search                           | Pattern matching                   |
| `bloom`      | Bloom filter search                                 | Membership testing with large data |
| `boyermoore` | Boyer-Moore search                                  | Text processing                    |
| `kmp`        | Knuth-Morris-Pratt search                           | Partial string matching            |
| `rabinkarp`  | Rabin-Karp search                                   | Multiple pattern searching         |

## Testing

Run the test suite with pytest:

```bash
pytest tests
```

## Protocol

The server implements a simple text-based protocol:

- **Request**: Plain text query string
- **Response**: 
  - `STRING EXISTS` - if the string is found
  - `STRING NOT FOUND` - if the string is not found

## Service Management

- **Check status**: `systemctl status search-server.service`
- **View logs**: `sudo journalctl -u search-server.service -f`
- **Restart service**: `sudo systemctl restart search-server.service`
- **Stop service**: `sudo systemctl stop search-server.service`

## Project Structure

```
.
├── benchmarks/          # Performance benchmarks
├── certs/               # SSL certificates
├── data/                # Search data files
├── logs/                # Log files
├── scripts/             # Helper scripts
├── service/             # Service installation files
├── src/                 # Main package
│   ├── client/          # Client implementation
│   ├── config/          # Configuration handling
│   ├── search/          # Search algorithms
│   └── server/          # Server implementation
└── tests/               # Test suite
```
