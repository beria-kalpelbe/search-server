import socket
import ssl
import time
from algo_science.config.config import Config

def test_search(query: str, use_ssl: bool = True) -> str:
    """Send a search query to the server and return the response.
    
    Args:
        query: Search string to look for
        use_ssl: Whether to use SSL connection
        
    Returns:
        Server response (STRING EXISTS or STRING NOT FOUND)
    """
    try:
        # Create a socket object
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        if use_ssl:
            # Create SSL context
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            s = context.wrap_socket(s, server_hostname='localhost')
        
        # Load config to get server settings
        config = Config()
        
        # Connect to the server
        s.connect((config.host, config.port))
        
        # Send search query
        s.sendall(f"{query}\n".encode('utf-8'))
        
        # Receive response
        response = s.recv(1024).decode('utf-8').strip()
        print(f"Query '{query}': {response}")
        
        # Close the connection
        s.close()
        return response
        
    except Exception as e:
        print(f"Error searching for '{query}': {e}")
        return f"ERROR: {str(e)}"

def main():
    # Load config to check SSL setting
    config = Config()
    use_ssl = config.use_ssl
    
    print(f"Using SSL: {use_ssl}")
    print(f"Server: {config.host}:{config.port}")
    print("Testing search functionality...")
    
    # Test some sample queries
    test_queries = [
        "example",
        "test",
        "nonexistent",
        "algorithm",
        "search"
    ]
    
    for query in test_queries:
        test_search(query, use_ssl)
        time.sleep(0.5)  # Small delay between queries
    
    print("Test completed!")

if __name__ == "__main__":
    main() 