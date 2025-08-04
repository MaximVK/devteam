#!/usr/bin/env python3
"""Check status of all DevTeam services"""

import requests
import json

def check_service(name, url):
    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            data = response.json() if response.headers.get('content-type') == 'application/json' else response.text
            return f"✅ {name}: Running", data
        else:
            return f"⚠️  {name}: Status {response.status_code}", None
    except requests.exceptions.ConnectionError:
        return f"❌ {name}: Not running", None
    except Exception as e:
        return f"❌ {name}: Error - {e}", None

print("🔍 DevTeam Status Check")
print("=" * 50)

# Check web services
print("\n🌐 Web Services:")
web_status, _ = check_service("Web Backend API", "http://localhost:8000/docs")
print(f"  {web_status}")
if "Running" in web_status:
    print(f"     API Docs: http://localhost:8000/docs")

frontend_status, _ = check_service("Web Frontend", "http://localhost:3000/")
print(f"  {frontend_status}")
if "Running" in frontend_status:
    print(f"     Dashboard: http://localhost:3000")

# Check tool server
print("\n🔧 Tool Services:")
tool_status, _ = check_service("Tool Server", "http://localhost:8500/status")
print(f"  {tool_status}")

print("\n💡 Tips:")
print("  - Access the web dashboard at: http://localhost:3000")
print("  - Projects and agents are managed through the web interface")
print("  - Check logs in: ./logs/")