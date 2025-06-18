#!/usr/bin/env python3
"""
Performance Monitor - Diagnose system slowness and provide optimization recommendations.
This script helps identify bottlenecks in the multi-agent system.
"""

import asyncio
import time
import psutil
import sys
import os
from datetime import datetime
from typing import Dict, Any, List

class PerformanceMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.checks = []
        
    def add_check(self, name: str, result: bool, details: str, recommendation: str = None):
        """Add a performance check result."""
        self.checks.append({
            "name": name,
            "result": result,
            "details": details,
            "recommendation": recommendation,
            "timestamp": datetime.now().isoformat()
        })
    
    async def check_system_resources(self):
        """Check system resource availability."""
        print("🔍 Checking system resources...")
        
        # CPU check
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_ok = cpu_percent < 80
        self.add_check(
            "CPU Usage",
            cpu_ok,
            f"Current CPU usage: {cpu_percent:.1f}%",
            "Consider reducing agent check intervals if CPU usage is high"
        )
        
        # Memory check
        memory = psutil.virtual_memory()
        memory_ok = memory.percent < 85
        self.add_check(
            "Memory Usage",
            memory_ok,
            f"Memory usage: {memory.percent:.1f}% ({memory.available / 1024**3:.1f}GB available)",
            "Close unnecessary applications or increase system memory"
        )
        
        # Disk check
        disk = psutil.disk_usage('C:\\' if sys.platform == 'win32' else '/')
        disk_ok = disk.percent < 90
        self.add_check(
            "Disk Space",
            disk_ok,
            f"Disk usage: {disk.percent:.1f}% ({disk.free / 1024**3:.1f}GB free)",
            "Clean up disk space or move data to external storage"
        )
        
        # Network check
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('localhost', 8003))
            network_ok = result == 0
            sock.close()
            self.add_check(
                "Web Interface",
                network_ok,
                f"Web interface port 8003: {'Available' if network_ok else 'Not accessible'}",
                "Check if web interface is running on port 8003"
            )
        except Exception as e:
            self.add_check(
                "Web Interface",
                False,
                f"Network check failed: {e}",
                "Verify network configuration"
            )
    
    async def check_file_permissions(self):
        """Check file and directory permissions."""
        print("🔍 Checking file permissions...")
        
        # Log directory
        log_dir = "debug_output"
        try:
            os.makedirs(log_dir, exist_ok=True)
            test_file = os.path.join(log_dir, "test_write.tmp")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            self.add_check(
                "Log Directory Write",
                True,
                f"Log directory '{log_dir}' is writable",
                None
            )
        except Exception as e:
            self.add_check(
                "Log Directory Write",
                False,
                f"Cannot write to log directory: {e}",
                "Check directory permissions and disk space"
            )
        
        # Database directory
        db_dir = "data"
        try:
            os.makedirs(db_dir, exist_ok=True)
            test_file = os.path.join(db_dir, "test_write.tmp")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            self.add_check(
                "Database Directory Write",
                True,
                f"Database directory '{db_dir}' is writable",
                None
            )
        except Exception as e:
            self.add_check(
                "Database Directory Write",
                False,
                f"Cannot write to database directory: {e}",
                "Check directory permissions and disk space"
            )
    
    async def check_python_environment(self):
        """Check Python environment and dependencies."""
        print("🔍 Checking Python environment...")
        
        # Python version
        python_version = sys.version_info
        version_ok = python_version >= (3, 8)
        self.add_check(
            "Python Version",
            version_ok,
            f"Python {python_version.major}.{python_version.minor}.{python_version.micro}",
            "Upgrade to Python 3.8+ if using older version"
        )
        
        # Required packages
        required_packages = [
            "fastapi", "uvicorn", "psutil", "asyncio", "sqlite3"
        ]
        
        for package in required_packages:
            try:
                __import__(package)
                self.add_check(
                    f"Package: {package}",
                    True,
                    f"Package '{package}' is available",
                    None
                )
            except ImportError:
                self.add_check(
                    f"Package: {package}",
                    False,
                    f"Package '{package}' is missing",
                    f"Install package: pip install {package}"
                )
    
    async def check_agent_system(self):
        """Check if the agent system is running and accessible."""
        print("🔍 Checking agent system...")
        
        try:
            # Try to import orchestrator
            from system_orchestrator import orchestrator
            
            # Check if agents are accessible
            agent_count = len(orchestrator.agents) if hasattr(orchestrator, 'agents') else 0
            self.add_check(
                "Agent System",
                agent_count > 0,
                f"Found {agent_count} agents in orchestrator",
                "Ensure agent system is properly initialized"
            )
            
            # Check message bus
            try:
                from utils.message_bus import message_bus
                self.add_check(
                    "Message Bus",
                    True,
                    "Message bus is available",
                    None
                )
            except Exception as e:
                self.add_check(
                    "Message Bus",
                    False,
                    f"Message bus error: {e}",
                    "Check message bus configuration"
                )
                
        except Exception as e:
            self.add_check(
                "Agent System",
                False,
                f"Agent system error: {e}",
                "Check system orchestrator and agent imports"
            )
    
    async def check_llm_provider(self):
        """Check LLM provider availability."""
        print("🔍 Checking LLM provider...")
        
        try:
            from utils.ollama_client import ollama_client
            is_healthy = await ollama_client.health_check()
            self.add_check(
                "Ollama LLM Provider",
                is_healthy,
                "Ollama is available and healthy" if is_healthy else "Ollama is not responding",
                "Start Ollama service or check configuration" if not is_healthy else None
            )
        except Exception as e:
            self.add_check(
                "Ollama LLM Provider",
                False,
                f"Ollama check failed: {e}",
                "Install and configure Ollama for AI features"
            )
    
    async def run_performance_analysis(self):
        """Run comprehensive performance analysis."""
        print("🚀 Starting Performance Analysis...")
        print("=" * 50)
        
        await self.check_system_resources()
        await self.check_file_permissions()
        await self.check_python_environment()
        await self.check_agent_system()
        await self.check_llm_provider()
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate a comprehensive performance report."""
        print("\n" + "=" * 50)
        print("📊 PERFORMANCE ANALYSIS REPORT")
        print("=" * 50)
        
        total_checks = len(self.checks)
        passed_checks = sum(1 for check in self.checks if check["result"])
        failed_checks = total_checks - passed_checks
        
        print(f"Total Checks: {total_checks}")
        print(f"Passed: {passed_checks} ✅")
        print(f"Failed: {failed_checks} ❌")
        print(f"Success Rate: {(passed_checks/total_checks)*100:.1f}%")
        
        if failed_checks == 0:
            print("\n🎉 All checks passed! System should perform well.")
        else:
            print(f"\n⚠️ {failed_checks} issues found. Recommendations:")
            
            for check in self.checks:
                if not check["result"]:
                    print(f"\n❌ {check['name']}")
                    print(f"   Details: {check['details']}")
                    if check['recommendation']:
                        print(f"   Recommendation: {check['recommendation']}")
        
        # Performance recommendations
        print("\n" + "=" * 50)
        print("💡 GENERAL PERFORMANCE RECOMMENDATIONS")
        print("=" * 50)
        
        recommendations = [
            "1. Ensure adequate system resources (CPU < 80%, Memory < 85%, Disk < 90%)",
            "2. Use SSD storage for better database performance",
            "3. Close unnecessary applications while running the system",
            "4. Consider reducing agent check intervals if system is under load",
            "5. Monitor log file size and implement log rotation",
            "6. Use caching for frequently accessed data",
            "7. Ensure proper network connectivity for web interface",
            "8. Keep Python packages updated",
            "9. Consider using a production WSGI server for better performance",
            "10. Monitor system resources regularly"
        ]
        
        for rec in recommendations:
            print(rec)
        
        print(f"\n⏱️ Analysis completed in {time.time() - self.start_time:.2f} seconds")
        print("=" * 50)

async def main():
    """Main function to run performance analysis."""
    monitor = PerformanceMonitor()
    await monitor.run_performance_analysis()

if __name__ == "__main__":
    asyncio.run(main()) 