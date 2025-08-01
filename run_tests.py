#!/usr/bin/env python3
"""Simple test runner to verify test structure"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_test_files():
    """Check that all test files exist"""
    test_files = [
        "tests/__init__.py",
        "tests/conftest.py",
        "tests/unit/__init__.py",
        "tests/unit/test_claude_agent.py",
        "tests/unit/test_agent_api.py",
        "tests/unit/test_telegram_bridge.py",
        "tests/unit/test_github_sync.py",
        "tests/unit/test_orchestrator.py",
        "tests/integration/__init__.py",
        "tests/integration/test_web_api.py",
        "tests/integration/test_end_to_end.py",
    ]
    
    print("Checking test files...")
    all_exist = True
    
    for test_file in test_files:
        path = project_root / test_file
        if path.exists():
            print(f"✅ {test_file}")
        else:
            print(f"❌ {test_file} - NOT FOUND")
            all_exist = False
            
    return all_exist

def check_imports():
    """Check that basic imports work"""
    print("\nChecking imports...")
    
    try:
        # Check core modules can be imported
        modules = [
            "core.claude_agent",
            "agents.api",
            "web.backend",
        ]
        
        for module in modules:
            try:
                __import__(module)
                print(f"✅ {module}")
            except ImportError as e:
                print(f"❌ {module} - {e}")
                
    except Exception as e:
        print(f"Error checking imports: {e}")

def main():
    print("DevTeam Test Structure Verification")
    print("=" * 50)
    
    # Check test files
    files_ok = check_test_files()
    
    # Check imports
    check_imports()
    
    print("\n" + "=" * 50)
    if files_ok:
        print("✅ All test files are present!")
        print("\nTo run tests with pytest:")
        print("  poetry run pytest -v")
        print("\nTo run specific test file:")
        print("  poetry run pytest tests/unit/test_claude_agent.py -v")
    else:
        print("❌ Some test files are missing!")
        
if __name__ == "__main__":
    main()