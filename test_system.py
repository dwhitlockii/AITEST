#!/usr/bin/env python3
"""
Simple test script for the multi-agent monitoring system.
Tests basic functionality without web interface to avoid Unicode issues.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from system_orchestrator import SystemOrchestrator
from utils.logger import system_logger


async def test_system():
    """Test the multi-agent system with basic functionality."""

    print("🧪 Starting Multi-Agent System Test")
    print("=" * 50)

    try:
        # Create and start the orchestrator
        orchestrator = SystemOrchestrator()

        print("🚀 Starting system orchestrator...")
        await orchestrator.start()

        # Let the system run for a bit to collect some data
        print("⏳ Running system for 30 seconds to collect data...")
        await asyncio.sleep(30)

        # Get system status
        print("\n📊 System Status:")
        status = orchestrator.get_system_status()
        for key, value in status.items():
            print(f"  {key}: {value}")

        # Get agent statuses
        print("\n🤖 Agent Statuses:")
        agent_statuses = orchestrator.get_agent_statuses()
        for agent_name, status in agent_statuses.items():
            print(f"  {agent_name}: {status['status']} (uptime: {status['uptime']})")

        # Get recent metrics
        print("\n📈 Recent Metrics:")
        metrics = orchestrator.get_recent_metrics()
        if metrics:
            for metric in metrics[-5:]:  # Show last 5 metrics
                print(
                    f"  {metric['timestamp']}: CPU={metric['cpu_percent']}%, "
                    f"Memory={metric['memory_percent']}%, Disk={metric['disk_percent']}%"
                )
        else:
            print("  No metrics collected yet")

        # Get recent analysis
        print("\n🧠 Recent Analysis:")
        analysis = orchestrator.get_recent_analysis()
        if analysis:
            for item in analysis[-3:]:  # Show last 3 analysis items
                print(f"  {item['timestamp']}: {item['summary']}")
        else:
            print("  No analysis performed yet")

        # Stop the system
        print("\n🛑 Stopping system...")
        await orchestrator.stop()

        print("✅ Test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


def main():
    """Main entry point."""
    print("Multi-Agent System Test")
    print("This will test the basic functionality of the monitoring system.")
    print(
        "The system will run for 30 seconds to collect data and demonstrate operation."
    )
    print()

    # Run the test
    asyncio.run(test_system())


if __name__ == "__main__":
    main()
