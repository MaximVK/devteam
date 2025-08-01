#!/usr/bin/env python3
import anthropic
from config.settings import settings

print(f"Testing Anthropic API with key: {settings.anthropic_api_key[:20]}...")

try:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    print("✅ Client created successfully")
    
    # Test with a simple message
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=100,
        messages=[{"role": "user", "content": "Say hello"}]
    )
    print(f"✅ API Response: {response.content[0].text}")
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")