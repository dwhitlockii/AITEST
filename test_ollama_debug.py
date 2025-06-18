#!/usr/bin/env python3
"""
Debug script to test Ollama connectivity and identify timeout issues.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime


async def test_ollama_basic():
    """Test basic Ollama connectivity."""
    print("=== OLLAMA BASIC CONNECTIVITY TEST ===")

    base_url = "http://localhost:11434"

    # Test 1: Check if Ollama is running
    print("1. Testing if Ollama is running...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                print(f"   Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Ollama is running")
                    print(f"   Response keys: {list(data.keys())}")
                    if "models" in data:
                        models = [model.get("name", "") for model in data["models"]]
                        print(f"   Available models: {models}")
                    return True
                else:
                    print(f"   ❌ Ollama responded with status {response.status}")
                    return False
    except Exception as e:
        print(f"   ❌ Cannot connect to Ollama: {e}")
        return False


async def test_ollama_models():
    """Test model availability."""
    print("\n2. Testing model availability...")

    base_url = "http://localhost:11434"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if "models" in data:
                        models = [model.get("name", "") for model in data["models"]]
                        print(f"   ✅ Found {len(models)} models: {models}")
                        return models
                    else:
                        print(f"   ❌ No models in response: {data}")
                        return []
                else:
                    print(f"   ❌ Failed to get models: {response.status}")
                    return []
    except Exception as e:
        print(f"   ❌ Model test failed: {e}")
        return []


async def test_ollama_generate(model_name):
    """Test generate endpoint with a specific model."""
    print(f"\n3. Testing generate endpoint with model: {model_name}")

    base_url = "http://localhost:11434"

    test_payload = {
        "model": model_name,
        "prompt": "Say hello in one word",
        "stream": False,
        "options": {"num_predict": 10, "temperature": 0.7},
    }

    print(f"   Request payload: {json.dumps(test_payload, indent=2)}")

    try:
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            print(f"   Making POST request to {base_url}/api/generate")
            print(f"   Timeout: 15 seconds")

            async with session.post(
                f"{base_url}/api/generate",
                json=test_payload,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                request_time = time.time() - start_time
                print(f"   Response received in {request_time:.2f} seconds")
                print(f"   Status: {response.status}")
                print(f"   Headers: {dict(response.headers)}")

                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Generate successful")
                    print(f"   Response keys: {list(data.keys())}")
                    print(f"   Response text: {data.get('response', '')}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"   ❌ Generate failed: {response.status} - {error_text}")
                    return False
    except asyncio.TimeoutError:
        print(f"   ⏰ Generate request timed out after 15 seconds")
        return False
    except Exception as e:
        print(f"   ❌ Generate test failed: {e}")
        return False


async def test_ollama_with_different_models():
    """Test generate with different models."""
    print("\n4. Testing different models...")

    models = await test_ollama_models()
    if not models:
        print("   No models available for testing")
        return

    for model in models[:3]:  # Test first 3 models
        print(f"\n   Testing model: {model}")
        success = await test_ollama_generate(model)
        if success:
            print(f"   ✅ Model {model} works")
            break
        else:
            print(f"   ❌ Model {model} failed")


async def main():
    """Run all tests."""
    print("🔍 OLLAMA DEBUG TEST SCRIPT")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Test basic connectivity
    if not await test_ollama_basic():
        print("\n❌ Ollama is not running or not accessible")
        print("Please ensure Ollama is running on http://localhost:11434")
        return

    # Test models
    models = await test_ollama_models()
    if not models:
        print("\n❌ No models available")
        print(
            "Please pull a model: curl -X POST http://localhost:11434/api/pull -H 'Content-Type: application/json' -d '{\"name\":\"llama2:latest\"}'"
        )
        return

    # Test generate with different models
    await test_ollama_with_different_models()

    print("\n" + "=" * 50)
    print("🏁 Debug test completed")


if __name__ == "__main__":
    asyncio.run(main())
