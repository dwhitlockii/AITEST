"""
Base agent class for the multi-agent monitoring system.
This is the foundation that all agents build upon - like a superhero origin story.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

from config import config
from utils.logger import create_agent_logger
from utils.message_bus import Message, MessageType, MessagePriority, message_bus


class BaseAgent(ABC):
    """Base class for all agents in the monitoring system."""

    AGENT_TYPE_MAP = {
        "SensorAgent": "sensor",
        "AnalyzerAgent": "analyzer",
        "RemediatorAgent": "remediator",
        "CommunicatorAgent": "communicator",
    }

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.agent_type = self.AGENT_TYPE_MAP.get(agent_name, agent_name.lower())
        self.logger = create_agent_logger(agent_name)
        agent_type = self.agent_type
        self.config = config.get_agent_config(agent_type)
        if not self.config:
            raise ValueError(f"No configuration found for agent type: {agent_type}")

        # State management
        self.running = False
        self.start_time: Optional[datetime] = None
        self.last_check_time: Optional[datetime] = None
        self.check_count = 0
        self.error_count = 0
        self.success_count = 0

        # Message bus integration
        self.message_bus = message_bus
        self.subscribed_message_types: List[MessageType] = []

        # Performance tracking
        self.avg_response_time = 0.0
        self.total_processing_time = 0.0

        # Health and status
        self.health_status = "unknown"
        self.last_health_check = None
        self.issues_detected = []

        self.logger.info(f"Agent initialized: {agent_name}")

    async def start(self):
        """Start the agent and begin its main loop."""
        if self.running:
            self.logger.warning("Agent is already running")
            return

        self.running = True
        self.start_time = datetime.now()

        # Subscribe to relevant message types
        await self._setup_subscriptions()

        # Start the main agent loop
        self.logger.info(f"Starting agent: {self.agent_name}")
        await self._main_loop()

    async def stop(self):
        """Stop the agent gracefully."""
        if not self.running:
            return

        self.logger.info(f"Stopping agent: {self.agent_name}")
        self.running = False

        # Unsubscribe from message types
        await self._cleanup_subscriptions()

        # Perform any cleanup
        await self._cleanup()

        self.logger.info(f"Agent stopped: {self.agent_name}")

    async def _main_loop(self):
        """Main agent loop - the heart of the agent."""
        while self.running:
            try:
                start_time = time.time()

                # Perform the agent's primary function
                await self._perform_check()

                # Update performance metrics
                processing_time = time.time() - start_time
                self._update_performance_metrics(processing_time)

                # Update health status
                await self._update_health_status()

                # Ensure health_status is set to healthy after first success
                if self.success_count > 0 and self.health_status == "unknown":
                    self.health_status = "healthy"

                # Wait for next check interval
                await asyncio.sleep(self.config.check_interval)

            except asyncio.CancelledError:
                self.logger.info(f"Agent loop cancelled: {self.agent_name}")
                break
            except Exception as e:
                self.error_count += 1
                self.logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(5)  # Brief pause on error

    @abstractmethod
    async def _perform_check(self):
        """Perform the agent's primary function. Must be implemented by subclasses."""
        pass

    async def _setup_subscriptions(self):
        """Set up message subscriptions. Override in subclasses if needed."""
        # Subscribe to status updates by default
        await self.message_bus.subscribe(
            MessageType.STATUS_UPDATE, self._handle_status_update
        )
        self.subscribed_message_types.append(MessageType.STATUS_UPDATE)

        # Subscribe to system commands
        await self.message_bus.subscribe(
            MessageType.SYSTEM_COMMAND, self._handle_system_command
        )
        self.subscribed_message_types.append(MessageType.SYSTEM_COMMAND)

    async def _cleanup_subscriptions(self):
        """Clean up message subscriptions."""
        for message_type in self.subscribed_message_types:
            try:
                await self.message_bus.unsubscribe(
                    message_type, self._handle_status_update
                )
                await self.message_bus.unsubscribe(
                    message_type, self._handle_system_command
                )
            except Exception as e:
                self.logger.error(f"Error unsubscribing from {message_type}: {e}")

    async def _cleanup(self):
        """Perform any cleanup tasks. Override in subclasses if needed."""
        pass

    async def _handle_status_update(self, message: Message):
        """Handle status update messages."""
        if message.sender == self.agent_name:
            return  # Ignore our own messages

        self.logger.debug(
            f"Received status update from {message.sender}: {message.content}"
        )

    async def _handle_system_command(self, message: Message):
        """Handle system command messages and broadcast coordination."""
        command = message.content.get("command")
        target = message.content.get("target", "all")

        if target != "all" and target != self.agent_name:
            return  # Not for us

        self.logger.info(f"Received system command: {command}")

        # Broadcast coordination message for visibility
        await self.message_bus.broadcast(
            sender=self.agent_name,
            message_type=MessageType.COORDINATION,
            content={"info": f"{self.agent_name} received command '{command}'"},
            priority=MessagePriority.NORMAL,
        )

        if command == "status":
            await self._send_status_update()
        elif command == "health_check":
            await self._perform_health_check()
        elif command == "restart":
            await self.stop()
            await self.start()

    async def _send_status_update(self):
        """Send a status update to other agents."""
        status_data = {
            "agent_name": self.agent_name,
            "status": "running" if self.running else "stopped",
            "uptime": (
                (datetime.now() - self.start_time).total_seconds()
                if self.start_time
                else 0
            ),
            "check_count": self.check_count,
            "error_count": self.error_count,
            "success_count": self.success_count,
            "health_status": self.health_status,
            "avg_response_time": self.avg_response_time,
            "last_check_time": (
                self.last_check_time.isoformat() if self.last_check_time else None
            ),
        }

        await self.message_bus.broadcast(
            sender=self.agent_name,
            message_type=MessageType.STATUS_UPDATE,
            content=status_data,
            priority=MessagePriority.NORMAL,
        )

    async def _update_health_status(self):
        """Update the agent's health status."""
        if self.error_count > 10:
            self.health_status = "critical"
        elif self.error_count > 5:
            self.health_status = "warning"
        elif self.success_count > 0:
            self.health_status = "healthy"
        else:
            self.health_status = "unknown"

        self.last_health_check = datetime.now()

    async def _perform_health_check(self):
        """Perform a health check and report results."""
        health_data = {
            "agent_name": self.agent_name,
            "status": self.health_status,
            "running": self.running,
            "uptime": (
                (datetime.now() - self.start_time).total_seconds()
                if self.start_time
                else 0
            ),
            "error_rate": self.error_count / max(self.check_count, 1),
            "avg_response_time": self.avg_response_time,
            "issues": self.issues_detected,
        }

        await self.message_bus.broadcast(
            sender=self.agent_name,
            message_type=MessageType.HEALTH_CHECK,
            content=health_data,
            priority=MessagePriority.NORMAL,
        )

    def _update_performance_metrics(self, processing_time: float):
        """Update performance tracking metrics."""
        self.total_processing_time += processing_time
        self.check_count += 1

        # Calculate running average
        if self.check_count > 0:
            self.avg_response_time = self.total_processing_time / self.check_count

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return {
            "agent_name": self.agent_name,
            "running": self.running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime": (
                (datetime.now() - self.start_time).total_seconds()
                if self.start_time
                else 0
            ),
            "check_count": self.check_count,
            "error_count": self.error_count,
            "success_count": self.success_count,
            "health_status": self.health_status,
            "avg_response_time": self.avg_response_time,
            "last_check_time": (
                self.last_check_time.isoformat() if self.last_check_time else None
            ),
            "issues_detected": self.issues_detected,
        }

    def log_metric(
        self, metric_name: str, value: Any, threshold: Optional[float] = None
    ):
        """Log a metric with optional threshold comparison."""
        self.logger.metric(metric_name, value, threshold)

    def log_action(self, action: str, target: str, result: str = "initiated"):
        """Log an agent action."""
        self.logger.action(action, target, result)

    def log_gpt_decision(self, decision: str, reasoning: str):
        """Log a GPT-based decision."""
        self.logger.gpt_decision(decision, reasoning)

    def add_issue(self, issue: str, severity: str = "medium"):
        """Add an issue to the agent's issue tracking."""
        issue_data = {
            "description": issue,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
        }
        self.issues_detected.append(issue_data)

        # Keep only recent issues
        if len(self.issues_detected) > 10:
            self.issues_detected.pop(0)

    def clear_issues(self):
        """Clear all tracked issues."""
        self.issues_detected.clear()
