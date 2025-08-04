#!/usr/bin/env python3
"""Fix SSL certificates for Poetry environment"""

import os
import ssl
import certifi
import subprocess
import sys

def main():
    # Get certificate locations
    cert_file = certifi.where()
    print(f"Certifi certificates location: {cert_file}")
    
    # Get Poetry Python executable
    result = subprocess.run(['poetry', 'run', 'which', 'python'], 
                          capture_output=True, text=True)
    python_path = result.stdout.strip()
    print(f"Poetry Python: {python_path}")
    
    # Set environment variables for the shell
    shell_config = os.path.expanduser("~/.zshrc")  # or ~/.bashrc for bash
    
    export_lines = f"""
# Poetry DevTeam SSL certificates
export SSL_CERT_FILE="{cert_file}"
export REQUESTS_CA_BUNDLE="{cert_file}"
"""
    
    print("\nAdd these lines to your shell configuration:")
    print(export_lines)
    
    # Create a .env file for the project
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    with open(env_file, 'w') as f:
        f.write(f'SSL_CERT_FILE="{cert_file}"\n')
        f.write(f'REQUESTS_CA_BUNDLE="{cert_file}"\n')
    
    print(f"\nCreated .env file: {env_file}")
    
    # Test SSL connection
    print("\nTesting SSL connection...")
    try:
        import urllib.request
        urllib.request.urlopen('https://www.google.com')
        print("✅ SSL connection successful!")
    except Exception as e:
        print(f"❌ SSL connection failed: {e}")

if __name__ == "__main__":
    main()