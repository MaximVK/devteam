"""Integration test for Anthropic client to debug proxy issues"""

import os
import pytest
import asyncio
from unittest.mock import patch

# Test the Anthropic client initialization issue


def test_anthropic_client_initialization():
    """Test different ways to initialize Anthropic client"""
    
    # Get API key from environment or config
    api_key = os.environ.get('ANTHROPIC_API_KEY', 'test-key')
    
    print("\n=== Testing Anthropic Client Initialization ===")
    
    # Test 1: Direct import and initialization
    print("\nTest 1: Direct initialization")
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        print("✓ Direct initialization successful")
    except Exception as e:
        print(f"✗ Direct initialization failed: {type(e).__name__}: {e}")
    
    # Test 2: Check environment variables
    print("\nTest 2: Environment variables check")
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 
                  'NO_PROXY', 'no_proxy', 'HTTPX_PROXY', 'httpx_proxy']
    found_vars = {}
    for var in proxy_vars:
        if var in os.environ:
            found_vars[var] = os.environ[var]
    
    if found_vars:
        print(f"Found proxy environment variables: {found_vars}")
    else:
        print("No proxy environment variables found")
    
    # Test 3: Initialize with cleared environment
    print("\nTest 3: Initialization with cleared environment")
    env_backup = os.environ.copy()
    try:
        # Clear all environment variables
        os.environ.clear()
        os.environ['ANTHROPIC_API_KEY'] = api_key
        
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        print("✓ Initialization with cleared environment successful")
    except Exception as e:
        print(f"✗ Initialization with cleared environment failed: {type(e).__name__}: {e}")
    finally:
        # Restore environment
        os.environ.clear()
        os.environ.update(env_backup)
    
    # Test 4: Initialize with custom httpx client
    print("\nTest 4: Initialization with custom httpx client")
    try:
        import anthropic
        import httpx
        
        # Create httpx client without proxy settings
        http_client = httpx.Client()
        
        # Try to pass custom client (if supported)
        try:
            client = anthropic.Anthropic(
                api_key=api_key,
                http_client=http_client
            )
            print("✓ Initialization with custom httpx client successful")
        except TypeError as e:
            print(f"✗ Custom http_client not supported: {e}")
            
    except Exception as e:
        print(f"✗ Initialization with custom httpx client failed: {type(e).__name__}: {e}")
    
    # Test 5: Check httpx version
    print("\nTest 5: Check httpx version")
    try:
        import httpx
        print(f"httpx version: {httpx.__version__}")
    except:
        print("httpx not available")
    
    # Test 6: Monkey patch approach
    print("\nTest 6: Monkey patch httpx.Client")
    try:
        import anthropic
        import httpx
        
        # Store original Client
        original_client = httpx.Client
        
        # Create a wrapper that filters out 'proxies' argument
        class ClientWrapper:
            def __init__(self, **kwargs):
                # Remove proxies argument if present
                kwargs.pop('proxies', None)
                self._client = original_client(**kwargs)
            
            def __getattr__(self, name):
                return getattr(self._client, name)
        
        # Monkey patch
        httpx.Client = ClientWrapper
        
        try:
            client = anthropic.Anthropic(api_key=api_key)
            print("✓ Monkey patch approach successful")
        finally:
            # Restore original
            httpx.Client = original_client
            
    except Exception as e:
        print(f"✗ Monkey patch approach failed: {type(e).__name__}: {e}")


@pytest.mark.asyncio
async def test_agent_anthropic_integration():
    """Test the actual agent integration with Anthropic"""
    from agents.base_agent import BaseAgent
    from pathlib import Path
    
    # Create a test agent
    agent = BaseAgent(
        agent_name="test-agent",
        port=8999,
        workspace_path=Path("/tmp/test-workspace")
    )
    
    # Set API key
    os.environ['ANTHROPIC_API_KEY'] = os.environ.get('ANTHROPIC_API_KEY', 'test-key')
    
    # Test process_message
    response = await agent.process_message("Hello, can you see this?")
    print(f"\nAgent response: {response}")
    
    assert response is not None
    assert isinstance(response, str)


def test_find_working_solution():
    """Find a working solution for the Anthropic client"""
    api_key = os.environ.get('ANTHROPIC_API_KEY', 'test-key')
    
    print("\n=== Finding Working Solution ===")
    
    # Solution: Use environment variable to disable proxy
    print("\nSolution: Set HTTPX_DISABLE_PROXY=1")
    os.environ['HTTPX_DISABLE_PROXY'] = '1'
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        print("✓ Solution works! Set HTTPX_DISABLE_PROXY=1 to disable proxy")
        
        # Test actual API call (if we have a real key)
        if api_key != 'test-key':
            try:
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=100,
                    messages=[{"role": "user", "content": "Say 'Hello, I'm working!'"}]
                )
                print(f"API Response: {response.content[0].text}")
            except Exception as e:
                print(f"API call failed: {e}")
                
    except Exception as e:
        print(f"✗ Solution failed: {type(e).__name__}: {e}")
    finally:
        # Clean up
        os.environ.pop('HTTPX_DISABLE_PROXY', None)


if __name__ == "__main__":
    # Run tests directly
    test_anthropic_client_initialization()
    test_find_working_solution()
    
    # Run async test
    asyncio.run(test_agent_anthropic_integration())