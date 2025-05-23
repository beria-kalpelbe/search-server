# Search Server

A high-performance server that checks if a string exists in a file using multiple search algorithms with SSL encryption support.

![Python](https://img.shields.io/badge/python-3.12-green.svg)

## Overview

### Features

- **Multiple Search Algorithms**: Choose from 10 different search implementations
- **High Performance**: Optimized for speed with configurable worker threads
- **Secure Communication**: Built-in SSL support with certificate management
- **Configurable**: Extensive configuration options via config files
- **Linux Daemon**: Runs as a system service for production deployments
- **Simple Protocol**: Text-based request/response communication

### Search Algorithms

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
| `grep`       | Leverages the `grep` command-line tool for search   | High-performance file scanning     |

## Installation

### Prerequisites

Set up Python environment -- Python 3.12:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Basic Setup

1. **Prepare data file**:
   ```bash
   cd data
   wget https://tests.quantitative-analysis.com/200k.txt
   cd ../
   ```

2. **Generate SSL certificates** (optional for secure connections):
   ```bash
   mkdir -p certs
   openssl req -x509 -newkey rsa:2048 -keyout certs/server.key \
     -out certs/server.crt -days 365 -nodes -subj "/CN=localhost"
   ```

### Configuration

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
REREAD_ON_QUERY = true

[LOGGING]
LEVEL = INFO
FILE = logs/server.log
```

### Production Deployment

Install as system service:
```bash
chmod +x service/install.sh
sudo service/install.sh
```

Verify installation:
```bash
systemctl status search-server.service
```

## Usage

### Client Interface

Use the client script to send search queries to the server:

```bash
python src/client/client.py --host localhost --port 8443 --queries "Existing line" "Nonexistent line"
```

#### Client Parameters

- `--host`: Server hostname (default: `localhost`)
- `--port`: Server port (default: `8443`)
- `--no-ssl`: Disable SSL for the connection
- `--cert`: Path to the server certificate for SSL verification
- `--queries`: List of search queries to send (default: `['test']`)
- `--threads`: Number of concurrent threads to use (default: `10`)

### Protocol

The server implements a simple text-based protocol:

**Request**: Plain text query string
**Response**: 
- `STRING EXISTS` - if the string is found
- `STRING NOT FOUND` - if the string is not found

## Service Management

### Common Commands

- **Check status**: `systemctl status search-server.service`
- **View logs**: `sudo journalctl -u search-server.service -f`  
- **Restart service**: `sudo systemctl restart search-server.service`
- **Stop service**: `sudo systemctl stop search-server.service`

## Development

### Testing

Run the test suite with pytest:
```bash
pytest tests
```

### Project Structure

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