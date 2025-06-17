#!/usr/bin/env python3
"""
Test script for Ollama integration.
This script tests the Ollama client functionality without requiring API keys.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.ollama_client import ollama_client
from config import config


async def test_ollama_health():
    """Test if Ollama is available and healthy."""
    print("🔍 Testing Ollama health...")
    
    try:
        healthy = await ollama_client.health_check()
        if healthy:
            print("✅ Ollama is healthy and available")
            return True
        else:
            print("❌ Ollama is not responding")
            return False
    except Exception as e:
        print(f"❌ Ollama health check failed: {e}")
        return False


async def test_ollama_models():
    """Test listing available models."""
    print("\n📋 Testing model listing...")
    
    try:
        models = await ollama_client.list_models()
        if models:
            print(f"✅ Found {len(models)} models: {', '.join(models)}")
            return models
        else:
            print("⚠️  No models found. You may need to download a model:")
            print("   ollama pull llama2")
            return []
    except Exception as e:
        print(f"❌ Model listing failed: {e}")
        return []


async def test_ollama_analysis():
    """Test system analysis with Ollama."""
    print("\n🧠 Testing system analysis...")
    
    # Sample system metrics
    test_metrics = {
        "cpu": {
            "usage_percent": 75.5,
            "core_count": 8,
            "per_core_usage": [80, 70, 85, 75, 60, 65, 80, 70]
        },
        "memory": {
            "usage_percent": 85.2,
            "total_gb": 16.0,
            "available_gb": 2.4
        },
        "disk": {
            "C:\\": {
                "usage_percent": 92.1,
                "free_gb": 5.2
            }
        },
        "performance": {
            "system_load_score": 78.5,
            "health_status": "warning",
            "bottlenecks": ["High disk usage", "Memory pressure"]
        }
    }
    
    try:
        decision = await ollama_client.analyze_metrics(test_metrics, "Test analysis")
        
        print(f"✅ Analysis completed:")
        print(f"   Decision: {decision.decision}")
        print(f"   Reasoning: {decision.reasoning[:100]}...")
        print(f"   Confidence: {decision.confidence}")
        print(f"   Risk Level: {decision.risk_level}")
        print(f"   Alternatives: {decision.alternatives}")
        
        return True
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return False


async def test_ollama_remediation():
    """Test remediation recommendations with Ollama."""
    print("\n🔧 Testing remediation recommendations...")
    
    test_issue = "High disk usage detected on C: drive (92.1%)"
    test_metrics = {"disk_usage": 92.1, "available_space_gb": 5.2}
    available_actions = ["clean_temp_files", "clear_browser_cache", "restart_service"]
    
    try:
        decision = await ollama_client.recommend_remediation(
            test_issue, test_metrics, available_actions
        )
        
        print(f"✅ Remediation recommendation completed:")
        print(f"   Decision: {decision.decision}")
        print(f"   Reasoning: {decision.reasoning[:100]}...")
        print(f"   Confidence: {decision.confidence}")
        print(f"   Risk Level: {decision.risk_level}")
        print(f"   Alternatives: {decision.alternatives}")
        
        return True
    except Exception as e:
        print(f"❌ Remediation recommendation failed: {e}")
        return False


async def test_ollama_anomaly_detection():
    """Test anomaly detection with Ollama."""
    print("\n🚨 Testing anomaly detection...")
    
    test_metrics = {
        "cpu": {"usage_percent": 95.5},  # Unusually high
        "memory": {"usage_percent": 45.2},  # Normal
        "network": {"packets_dropped": 150}  # Anomalous
    }
    
    historical_context = [
        {"cpu": {"usage_percent": 25.0}, "timestamp": "2024-01-01T10:00:00"},
        {"cpu": {"usage_percent": 30.0}, "timestamp": "2024-01-01T10:01:00"},
        {"cpu": {"usage_percent": 95.5}, "timestamp": "2024-01-01T10:02:00"},  # Spike
    ]
    
    try:
        decision = await ollama_client.detect_anomalies(test_metrics, historical_context)
        
        print(f"✅ Anomaly detection completed:")
        print(f"   Decision: {decision.decision}")
        print(f"   Reasoning: {decision.reasoning[:100]}...")
        print(f"   Confidence: {decision.confidence}")
        print(f"   Risk Level: {decision.risk_level}")
        print(f"   Metadata: {decision.metadata}")
        
        return True
    except Exception as e:
        print(f"❌ Anomaly detection failed: {e}")
        return False


async def main():
    """Run all Ollama tests."""
    print("🦙 Ollama Integration Test Suite")
    print("=" * 50)
    
    # Test health
    health_ok = await test_ollama_health()
    if not health_ok:
        print("\n❌ Ollama is not available. Please:")
        print("   1. Install Ollama: https://ollama.ai/download")
        print("   2. Start Ollama: ollama serve")
        print("   3. Download a model: ollama pull llama2")
        return
    
    # Test models
    models = await test_ollama_models()
    if not models:
        print("\n⚠️  No models available. Please download a model:")
        print("   ollama pull llama2")
        return
    
    # Test functionality
    analysis_ok = await test_ollama_analysis()
    remediation_ok = await test_ollama_remediation()
    anomaly_ok = await test_ollama_anomaly_detection()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   Health Check: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"   Model Listing: {'✅ PASS' if models else '❌ FAIL'}")
    print(f"   System Analysis: {'✅ PASS' if analysis_ok else '❌ FAIL'}")
    print(f"   Remediation: {'✅ PASS' if remediation_ok else '❌ FAIL'}")
    print(f"   Anomaly Detection: {'✅ PASS' if anomaly_ok else '❌ FAIL'}")
    
    all_passed = health_ok and models and analysis_ok and remediation_ok and anomaly_ok
    
    if all_passed:
        print("\n🎉 All tests passed! Ollama integration is working correctly.")
        print("\nNext steps:")
        print("   1. Start the main system: python system_orchestrator.py")
        print("   2. Open web interface: http://localhost:8000")
        print("   3. Check LLM Status section to see Ollama in action")
    else:
        print("\n⚠️  Some tests failed. Please check the error messages above.")
        print("\nTroubleshooting:")
        print("   1. Ensure Ollama is running: ollama serve")
        print("   2. Check model availability: ollama list")
        print("   3. Download a model if needed: ollama pull llama2")
        print("   4. Check Ollama logs for errors")


if __name__ == "__main__":
    asyncio.run(main()) 