"""Script to generate SSL certificates for the server."""

import os
import subprocess
import argparse

def generate_certificates(output_dir: str = ".") -> None:
    """Generate SSL certificates for the server.
    
    Args:
        output_dir: Directory to save certificates in
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate private key
    key_file = os.path.join(output_dir, "server.key")
    subprocess.run([
        "openssl", "genrsa",
        "-out", key_file,
        "2048"
    ], check=True)
    
    # Generate certificate signing request
    csr_file = os.path.join(output_dir, "server.csr")
    subprocess.run([
        "openssl", "req",
        "-new",
        "-key", key_file,
        "-out", csr_file,
        "-subj", "/CN=localhost"
    ], check=True)
    
    # Generate self-signed certificate
    cert_file = os.path.join(output_dir, "server.crt")
    subprocess.run([
        "openssl", "x509",
        "-req",
        "-days", "365",
        "-in", csr_file,
        "-signkey", key_file,
        "-out", cert_file
    ], check=True)
    
    # Clean up CSR
    os.unlink(csr_file)
    
    print(f"Generated certificates in {output_dir}:")
    print(f"- Private key: {key_file}")
    print(f"- Certificate: {cert_file}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate SSL certificates")
    parser.add_argument("--output-dir", default="certs",
                      help="Directory to save certificates in")
    args = parser.parse_args()
    
    try:
        generate_certificates(args.output_dir)
    except subprocess.CalledProcessError as e:
        print(f"Error generating certificates: {e}")
        exit(1)

if __name__ == "__main__":
    main() 