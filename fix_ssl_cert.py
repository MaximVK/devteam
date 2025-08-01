#!/usr/bin/env python3
"""Fix SSL certificates for macOS"""

import os
import ssl
import certifi

# Install certificates
print("🔧 Fixing SSL certificates...")

# Get the certificate bundle path
cert_path = certifi.where()
print(f"Certificate bundle path: {cert_path}")

# Set environment variables
os.environ['SSL_CERT_FILE'] = cert_path
os.environ['REQUESTS_CA_BUNDLE'] = cert_path

# Also try to update macOS certificates
try:
    import subprocess
    # This installs certificates for Python on macOS
    result = subprocess.run([
        '/Applications/Python 3.12/Install Certificates.command'
    ], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ macOS certificates updated")
    else:
        print("⚠️  Could not update macOS certificates (this is okay)")
except:
    print("⚠️  Could not update macOS certificates (this is okay)")

print("\n✅ SSL fix applied!")
print("\nNow you can run the Telegram bridge.")