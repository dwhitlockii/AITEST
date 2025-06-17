"""
System Orchestrator - The conductor of the multi-agent symphony.
This is the main entry point that coordinates all agents and manages the overall system.
Think of it as the air traffic controller for all our AI agents.
"""

import asyncio
import signal
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime

from agents import SensorAgent, AnalyzerAgent, RemediatorAgent, CommunicatorAgent
from utils.message_bus import message_bus, MessagePriority
from utils.logger import system_logger
from config import config

class SystemOrchestrator:
    """Main orchestrator for the multi-agent monitoring system."""
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.running = False
        self.startup_time: Optional[datetime] = None
        self.shutdown_requested = False
        
        # Agent tasks
        self.agent_tasks: Dict[str, asyncio.Task] = {}
        
        # System health
        self.system_health = "unknown"
        self.last_health_check = None
        
        system_logger.startup("System orchestrator initialized")
    
    async def start(self):
        """Start the entire multi-agent system."""
        if self.running:
            system_logger.startup("System is already running")
            return
        
        try:
            system_logger.startup("Starting multi-agent monitoring system...")
            self.running = True
            self.startup_time = datetime.now()
            
            # Start message bus
            await message_bus.start()
            system_logger.startup("Message bus started")
            
            # Initialize agents
            await self._initialize_agents()
            system_logger.startup("All agents initialized")
            
            # Start agents
            await self._start_agents()
            system_logger.startup("All agents started")
            
            # Start system monitoring
            asyncio.create_task(self._system_monitor_loop())
            system_logger.startup("System monitoring started")
            
            # Start health check loop
            asyncio.create_task(self._health_check_loop())
            system_logger.startup("Health check loop started")
            
            system_logger.startup("Multi-agent system is now operational!")
            
            # Keep the system running
            await self._main_loop()
            
        except Exception as e:
            system_logger.startup(f"Failed to start system: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the entire multi-agent system."""
        if not self.running:
            return
        
        system_logger.shutdown("Shutting down multi-agent system...")
        self.running = False
        self.shutdown_requested = True
        
        try:
            # Stop all agents
            await self._stop_agents()
            system_logger.shutdown("All agents stopped")
            
            # Stop message bus
            await message_bus.stop()
            system_logger.shutdown("Message bus stopped")
            
            system_logger.shutdown("Multi-agent system shutdown complete")
            
        except Exception as e:
            system_logger.shutdown(f"Error during shutdown: {e}")
    
    async def _initialize_agents(self):
        """Initialize all agents."""
        try:
            # Create agent instances
            self.agents["sensor"] = SensorAgent()
            self.agents["analyzer"] = AnalyzerAgent()
            self.agents["remediator"] = RemediatorAgent()
            self.agents["communicator"] = CommunicatorAgent()
            
            system_logger.startup(f"Created {len(self.agents)} agent instances")
            
        except Exception as e:
            system_logger.startup(f"Failed to initialize agents: {e}")
            raise
    
    async def _start_agents(self):
        """Start all agents."""
        for agent_name, agent in self.agents.items():
            try:
                # Create task for agent
                task = asyncio.create_task(agent.start())
                self.agent_tasks[agent_name] = task
                
                system_logger.startup(f"Started {agent_name}")
                
                # Brief pause between agent starts
                await asyncio.sleep(1)
                
            except Exception as e:
                system_logger.startup(f"Failed to start {agent_name}: {e}")
                raise
    
    async def _stop_agents(self):
        """Stop all agents."""
        for agent_name, agent in self.agents.items():
            try:
                await agent.stop()
                system_logger.shutdown(f"Stopped {agent_name}")
            except Exception as e:
                system_logger.shutdown(f"Error stopping {agent_name}: {e}")
        
        # Cancel agent tasks
        for task_name, task in self.agent_tasks.items():
            try:
                task.cancel()
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                system_logger.shutdown(f"Error cancelling task {task_name}: {e}")
        
        self.agent_tasks.clear()
    
    async def _main_loop(self):
        """Main system loop."""
        try:
            while self.running and not self.shutdown_requested:
                await asyncio.sleep(1)
                
                # Check if any agent tasks have failed
                await self._check_agent_health()
                
        except asyncio.CancelledError:
            system_logger.shutdown("Main loop cancelled")
        except Exception as e:
            system_logger.shutdown(f"Error in main loop: {e}")
    
    async def _system_monitor_loop(self):
        """Monitor overall system health."""
        try:
            while self.running and not self.shutdown_requested:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Update system health
                await self._update_system_health()
                
                # Log system status
                await self._log_system_status()
                
        except asyncio.CancelledError:
            system_logger.shutdown("System monitor loop cancelled")
        except Exception as e:
            system_logger.shutdown(f"Error in system monitor loop: {e}")
    
    async def _health_check_loop(self):
        """Perform periodic health checks."""
        try:
            while self.running and not self.shutdown_requested:
                await asyncio.sleep(60)  # Health check every minute
                health_data = await self._perform_health_check()
                await message_bus.broadcast(
                    sender="orchestrator",
                    message_type="health_check",
                    content=health_data,
                    priority=MessagePriority.NORMAL
                )
        except asyncio.CancelledError:
            system_logger.shutdown("Health check loop cancelled")
        except Exception as e:
            system_logger.shutdown(f"Error in health check loop: {e}")
    
    async def _check_agent_health(self):
        """Check if all agents are healthy."""
        for agent_name, task in self.agent_tasks.items():
            if task.done():
                try:
                    # Check if task completed successfully
                    await task
                except Exception as e:
                    system_logger.shutdown(f"Agent {agent_name} failed: {e}")
                    
                    # Attempt to restart the agent
                    await self._restart_agent(agent_name)
    
    async def _restart_agent(self, agent_name: str):
        """Restart a failed agent."""
        try:
            system_logger.startup(f"Attempting to restart {agent_name}")
            
            # Stop the agent
            if agent_name in self.agents:
                await self.agents[agent_name].stop()
            
            # Cancel the task
            if agent_name in self.agent_tasks:
                self.agent_tasks[agent_name].cancel()
                try:
                    await self.agent_tasks[agent_name]
                except asyncio.CancelledError:
                    pass
            
            # Recreate and restart the agent
            if agent_name == "sensor":
                self.agents[agent_name] = SensorAgent()
            elif agent_name == "analyzer":
                self.agents[agent_name] = AnalyzerAgent()
            elif agent_name == "remediator":
                self.agents[agent_name] = RemediatorAgent()
            elif agent_name == "communicator":
                self.agents[agent_name] = CommunicatorAgent()
            
            # Start the agent
            task = asyncio.create_task(self.agents[agent_name].start())
            self.agent_tasks[agent_name] = task
            
            system_logger.startup(f"Successfully restarted {agent_name}")
            
        except Exception as e:
            system_logger.shutdown(f"Failed to restart {agent_name}: {e}")
    
    async def _update_system_health(self):
        """Update overall system health status."""
        try:
            # Check agent health
            healthy_agents = 0
            total_agents = len(self.agents)
            
            for agent_name, agent in self.agents.items():
                if agent.health_status == "healthy":
                    healthy_agents += 1
            
            # Determine system health
            if healthy_agents == total_agents:
                self.system_health = "healthy"
            elif healthy_agents >= total_agents * 0.75:
                self.system_health = "warning"
            else:
                self.system_health = "critical"
            
            self.last_health_check = datetime.now()
            
        except Exception as e:
            system_logger.shutdown(f"Error updating system health: {e}")
    
    async def _log_system_status(self):
        """Log current system status."""
        try:
            uptime = (datetime.now() - self.startup_time).total_seconds() if self.startup_time else 0
            
            status_data = {
                "system_health": self.system_health,
                "uptime_seconds": uptime,
                "total_agents": len(self.agents),
                "running_agents": sum(1 for agent in self.agents.values() if agent.running),
                "agent_health": {name: agent.health_status for name, agent in self.agents.items()}
            }
            
            system_logger.health_check(self.system_health, status_data)
            
        except Exception as e:
            system_logger.shutdown(f"Error logging system status: {e}")
    
    async def _get_system_metrics(self) -> Dict[str, Any]:
        """Get basic system metrics for health checks."""
        try:
            import psutil
            
            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": {},
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting system metrics: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    async def _perform_health_check(self):
        """Perform a comprehensive health check of all agents."""
        try:
            health_data = {
                "timestamp": datetime.now().isoformat(),
                "overall_status": "healthy",
                "agents": {},
                "system_metrics": await self._get_system_metrics(),
                "issues": []
            }
            
            # Check each agent's health
            for agent_name, agent in self.agents.items():
                try:
                    stats = agent.get_stats()
                    
                    # Calculate uptime properly
                    uptime = 0
                    if stats.get("start_time"):
                        start_time = datetime.fromisoformat(stats["start_time"])
                        uptime = (datetime.now() - start_time).total_seconds()
                    
                    agent_health = {
                        "status": stats.get("health_status", "unknown"),
                        "running": stats.get("running", False),
                        "uptime": uptime,
                        "error_count": stats.get("error_count", 0),
                        "success_count": stats.get("success_count", 0),
                        "avg_response_time": stats.get("avg_response_time", 0),
                        "issues": stats.get("issues_detected", [])
                    }
                    
                    health_data["agents"][agent_name] = agent_health
                    
                    # Check for issues
                    if agent_health["status"] == "critical":
                        health_data["overall_status"] = "critical"
                        health_data["issues"].append(f"Agent {agent_name} is in critical condition")
                    elif agent_health["status"] == "warning" and health_data["overall_status"] == "healthy":
                        health_data["overall_status"] = "warning"
                        health_data["issues"].append(f"Agent {agent_name} is showing warning signs")
                        
                except Exception as e:
                    self.logger.error(f"Error checking health of {agent_name}: {e}")
                    health_data["agents"][agent_name] = {"status": "error", "error": str(e)}
            
            # Store health data
            self.health_history.append(health_data)
            if len(self.health_history) > 100:
                self.health_history.pop(0)
            
            # Log health status
            system_logger.health_check(health_data["overall_status"], health_data)
            
            return health_data
            
        except Exception as e:
            self.logger.error(f"Error performing health check: {e}")
            return None
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information."""
        try:
            total_agents = len(self.agents)
            running_agents = sum(1 for agent in self.agents.values() if getattr(agent, 'running', False))
            uptime = (datetime.now() - self.startup_time).total_seconds() if self.startup_time else 0
            agent_details = {}
            for name, agent in self.agents.items():
                # Ensure agent_type is present
                agent_type = getattr(agent, 'agent_type', name)
                if not hasattr(agent, 'agent_type'):
                    setattr(agent, 'agent_type', agent_type)
                agent_details[name] = {
                    "type": agent_type,
                    "status": "running" if getattr(agent, 'running', False) else "stopped",
                    "health": getattr(agent, 'health_status', 'unknown'),
                    "uptime": (datetime.now() - agent.start_time).total_seconds() if getattr(agent, 'start_time', None) else 0,
                    "check_count": getattr(agent, 'check_count', 0),
                    "error_count": getattr(agent, 'error_count', 0),
                    "success_count": getattr(agent, 'success_count', 0)
                }
            return {
                "system_health": self.system_health or "unknown",
                "startup_time": self.startup_time.isoformat() if self.startup_time else None,
                "uptime": uptime,
                "total_agents": total_agents,
                "running_agents": running_agents,
                "agent_details": agent_details,
                "message_bus_stats": message_bus.get_stats(),
                "config": config.to_dict()
            }
        except Exception as e:
            return {"error": f"Failed to get system info: {str(e)}"}
    
    def get_agent_stats(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific agent."""
        if agent_name in self.agents:
            return self.agents[agent_name].get_stats()
        return None
    
    async def send_command(self, command: str, target: str = "all"):
        """Send a command to agents and broadcast coordination message."""
        try:
            await message_bus.broadcast(
                sender="orchestrator",
                message_type="system_command",
                content={"command": command, "target": target},
                priority=MessagePriority.NORMAL
            )
            # Broadcast a coordination message for visibility
            await message_bus.broadcast(
                sender="orchestrator",
                message_type="coordination",
                content={"info": f"Command '{command}' sent to {target}"},
                priority=MessagePriority.NORMAL
            )
            system_logger.startup(f"Command '{command}' sent to {target}")
        except Exception as e:
            system_logger.shutdown(f"Error sending command: {e}")

    def get_system_status(self) -> dict:
        """Return a summary of system health for test script."""
        return {
            "system_health": self.system_health,
            "uptime": (datetime.now() - self.startup_time).total_seconds() if self.startup_time else 0,
            "total_agents": len(self.agents),
            "running_agents": sum(1 for agent in self.agents.values() if agent.running)
        }

    def get_agent_statuses(self) -> dict:
        """Return status for all agents for test script."""
        return {
            name: {
                "status": "running" if agent.running else "stopped",
                "uptime": (datetime.now() - agent.start_time).total_seconds() if agent.start_time else 0
            } for name, agent in self.agents.items()
        }

    def get_recent_metrics(self) -> list:
        """Return recent metrics from sensor agent for test script."""
        sensor = self.agents.get("sensor")
        if sensor and hasattr(sensor, 'get_metric_history'):
            return sensor.get_metric_history(5)
        return []

    def get_recent_analysis(self) -> list:
        """Return recent analysis from analyzer agent for test script."""
        analyzer = self.agents.get("analyzer")
        if analyzer and hasattr(analyzer, 'analysis_history'):
            return analyzer.analysis_history[-3:]
        return []

# Global orchestrator instance
orchestrator = SystemOrchestrator()

async def main():
    """Main entry point for the multi-agent system."""
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print("\n🛑 Shutdown signal received. Stopping system...")
        orchestrator.shutdown_requested = True
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start the system
        await orchestrator.start()
        
    except KeyboardInterrupt:
        print("\n🛑 Keyboard interrupt received. Stopping system...")
    except Exception as e:
        print(f"💥 System error: {e}")
    finally:
        # Ensure clean shutdown
        await orchestrator.stop()

if __name__ == "__main__":
    # Run the system
    asyncio.run(main()) 