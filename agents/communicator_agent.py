"""
CommunicatorAgent - The mouthpiece that keeps everyone informed.
This agent logs everything, sends status updates, and communicates with users.
Think of it as the PR department and customer service rolled into one.
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from agents.base_agent import BaseAgent
from utils.message_bus import MessageType, MessagePriority
from config import config
from utils.persistence import PersistenceManager


class CommunicatorAgent(BaseAgent):
    """Agent responsible for communication, logging, and status reporting."""

    def __init__(self):
        super().__init__("CommunicatorAgent")

        # Communication state
        self.message_history: List[Dict[str, Any]] = []
        self.agent_status: Dict[str, Dict[str, Any]] = {}
        self.system_health_history: List[Dict[str, Any]] = []
        self.user_notifications: List[Dict[str, Any]] = []

        # Status tracking
        self.last_system_summary = None
        self.summary_interval = 60  # seconds

        # Communication channels
        self.log_file = config.logging.log_file
        self.status_file = "debug_output/system_status.json"

        # Ensure output directory exists
        os.makedirs("debug_output", exist_ok=True)

        # Persistence integration
        self.persistence_enabled = getattr(config, "persistence_enabled", True)
        self.db_path = getattr(config, "db_path", "data/agent_system.db")
        self.persistence = PersistenceManager(self.db_path)

        self.logger.info(
            "CommunicatorAgent initialized - ready to keep everyone in the loop"
        )

        # LLM quota alert state
        self.llm_quota_alert_active = False
        self.llm_quota_alert_message = None

    async def _perform_check(self):
        """Handle communication tasks and status updates."""
        try:
            self.last_check_time = datetime.now()

            # Process incoming messages
            await self._process_incoming_messages()

            # Update agent status
            await self._update_agent_status()

            # Generate system summary
            await self._generate_system_summary()

            # Send status updates
            await self._send_status_updates()

            # Handle user notifications
            await self._handle_user_notifications()

            # Clean up old data
            self._cleanup_old_data()

            self.success_count += 1

        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Failed to perform communication tasks: {e}")
            self.add_issue(f"Communication failed: {str(e)}", "medium")

    async def _process_incoming_messages(self):
        """Process incoming messages from other agents."""
        # In a real implementation, you'd process messages from the message bus
        # For now, we'll simulate this by checking for any stored messages
        pass

    async def _update_agent_status(self):
        """Update status of all agents in the system."""
        # In a real implementation, you'd query the message bus for agent status
        # For now, we'll maintain a basic status structure
        current_time = datetime.now().isoformat()

        # Update our own status
        self.agent_status[self.agent_name] = {
            "status": "running" if self.running else "stopped",
            "health": self.health_status,
            "last_update": current_time,
            "uptime": (
                (datetime.now() - self.start_time).total_seconds()
                if self.start_time
                else 0
            ),
            "check_count": self.check_count,
            "error_count": self.error_count,
        }

    async def _generate_system_summary(self):
        """Generate a comprehensive system summary."""
        current_time = datetime.now()

        # Check if it's time for a new summary
        if (
            self.last_system_summary
            and (current_time - self.last_system_summary).seconds
            < self.summary_interval
        ):
            return

        self.last_system_summary = current_time

        try:
            # Gather system information
            summary = {
                "timestamp": current_time.isoformat(),
                "system_overview": await self._get_system_overview(),
                "agent_status": dict(self.agent_status),
                "recent_events": self._get_recent_events(),
                "health_indicators": await self._get_health_indicators(),
                "performance_metrics": await self._get_performance_metrics(),
                "active_issues": self._get_active_issues(),
                "llm_quota_alert_active": getattr(
                    self, "llm_quota_alert_active", False
                ),
                "llm_quota_alert_message": getattr(
                    self, "llm_quota_alert_message", None
                ),
            }

            # Store summary
            self.system_health_history.append(summary)
            if len(self.system_health_history) > 50:
                self.system_health_history.pop(0)

            # Persist summary if enabled (optional, for audit)
            if self.persistence_enabled:
                try:
                    await self.persistence.insert_analysis(
                        timestamp=summary["timestamp"],
                        agent=self.agent_name,
                        summary="System summary",
                        issues=str(summary.get("active_issues", [])),
                    )
                except Exception as e:
                    self.logger.error(f"Failed to persist system summary: {e}")
                    self.add_issue(f"Persistence error: {str(e)}", "medium")

            # Log summary
            self._log_system_summary(summary)

            # Save to file
            await self._save_system_status(summary)

        except Exception as e:
            self.logger.error(f"Failed to generate system summary: {e}")

    async def _get_system_overview(self) -> Dict[str, Any]:
        """Get a high-level system overview."""
        try:
            import psutil

            return {
                "platform": "Windows" if os.name == "nt" else "Unix/Linux",
                "cpu_usage": psutil.cpu_percent(),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": self._get_disk_usage(),
                "uptime": psutil.boot_time(),
                "total_agents": len(self.agent_status),
                "running_agents": sum(
                    1
                    for status in self.agent_status.values()
                    if status.get("status") == "running"
                ),
            }
        except Exception as e:
            self.logger.error(f"Failed to get system overview: {e}")
            return {"error": str(e)}

    def _get_disk_usage(self) -> Dict[str, float]:
        """Get disk usage for monitored paths."""
        try:
            import psutil

            disk_usage = {}
            for path in config.monitoring.disk_paths:
                try:
                    usage = psutil.disk_usage(path)
                    disk_usage[path] = (usage.used / usage.total) * 100
                except Exception:
                    disk_usage[path] = 0.0

            return disk_usage
        except Exception:
            return {}

    def _get_recent_events(self) -> List[Dict[str, Any]]:
        """Get recent system events."""
        events = []

        # Add recent messages
        for message in self.message_history[-10:]:
            events.append(
                {
                    "type": "message",
                    "timestamp": message.get("timestamp"),
                    "description": f"Message from {message.get('sender', 'unknown')}: {message.get('type', 'unknown')}",
                }
            )

        # Add recent notifications
        for notification in self.user_notifications[-5:]:
            events.append(
                {
                    "type": "notification",
                    "timestamp": notification.get("timestamp"),
                    "description": notification.get("message", "Unknown notification"),
                }
            )

        return events

    async def _get_health_indicators(self) -> Dict[str, Any]:
        """Get system health indicators."""
        try:
            import psutil

            indicators = {
                "cpu_health": "healthy",
                "memory_health": "healthy",
                "disk_health": "healthy",
                "overall_health": "healthy",
            }

            # CPU health
            cpu_usage = psutil.cpu_percent()
            if cpu_usage > config.thresholds.cpu_critical:
                indicators["cpu_health"] = "critical"
            elif cpu_usage > config.thresholds.cpu_warning:
                indicators["cpu_health"] = "warning"

            # Memory health
            memory_usage = psutil.virtual_memory().percent
            if memory_usage > config.thresholds.memory_critical:
                indicators["memory_health"] = "critical"
            elif memory_usage > config.thresholds.memory_warning:
                indicators["memory_health"] = "warning"

            # Disk health
            for path in config.monitoring.disk_paths:
                try:
                    usage = psutil.disk_usage(path)
                    disk_usage = (usage.used / usage.total) * 100
                    if disk_usage > config.thresholds.disk_critical:
                        indicators["disk_health"] = "critical"
                        break
                    elif disk_usage > config.thresholds.disk_warning:
                        indicators["disk_health"] = "warning"
                except Exception:
                    pass

            # Overall health
            if any(health == "critical" for health in indicators.values()):
                indicators["overall_health"] = "critical"
            elif any(health == "warning" for health in indicators.values()):
                indicators["overall_health"] = "warning"

            return indicators

        except Exception as e:
            self.logger.error(f"Failed to get health indicators: {e}")
            return {"error": str(e)}

    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        try:
            import psutil

            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_io": (
                    psutil.disk_io_counters()._asdict()
                    if psutil.disk_io_counters()
                    else {}
                ),
                "network_io": (
                    psutil.net_io_counters()._asdict()
                    if psutil.net_io_counters()
                    else {}
                ),
                "load_average": self._get_load_average(),
            }
        except Exception as e:
            self.logger.error(f"Failed to get performance metrics: {e}")
            return {"error": str(e)}

    def _get_load_average(self) -> Optional[float]:
        """Get system load average if available."""
        try:
            import psutil

            return psutil.getloadavg()[0] if hasattr(psutil, "getloadavg") else None
        except Exception:
            return None

    def _get_active_issues(self) -> List[Dict[str, Any]]:
        """Get currently active issues."""
        issues = []

        # Add issues from all agents
        for agent_name, status in self.agent_status.items():
            if status.get("health") in ["warning", "critical"]:
                issues.append(
                    {
                        "source": agent_name,
                        "severity": status.get("health"),
                        "description": f"Agent {agent_name} is in {status.get('health')} state",
                        "timestamp": status.get("last_update"),
                    }
                )

        # Add our own issues
        for issue in self.issues_detected:
            issues.append(
                {
                    "source": self.agent_name,
                    "severity": issue.get("severity", "medium"),
                    "description": issue.get("description", "Unknown issue"),
                    "timestamp": issue.get("timestamp"),
                }
            )

        return issues

    def _log_system_summary(self, summary: Dict[str, Any]):
        """Log the system summary with personality."""
        try:
            overview = summary.get("system_overview", {})
            health = summary.get("health_indicators", {})
            issues = summary.get("active_issues", [])

            # Log overall status
            overall_health = health.get("overall_health", "unknown")
            if overall_health == "healthy":
                self.logger.success(
                    "System is running smoothly - all systems operational"
                )
            elif overall_health == "warning":
                self.logger.warning(
                    "System showing some stress - keeping an eye on things"
                )
            elif overall_health == "critical":
                self.logger.critical(
                    "System is in critical condition - immediate attention required"
                )

            # Log key metrics
            if "cpu_usage" in overview:
                self.log_metric("System CPU", f"{overview['cpu_usage']:.1f}%")
            if "memory_usage" in overview:
                self.log_metric("System Memory", f"{overview['memory_usage']:.1f}%")

            # Log agent status
            running_agents = overview.get("running_agents", 0)
            total_agents = overview.get("total_agents", 0)
            self.logger.info(
                f"Agent status: {running_agents}/{total_agents} agents running"
            )

            # Log active issues
            if issues:
                self.logger.warning(
                    f"Active issues: {len(issues)} issues requiring attention"
                )
                for issue in issues[:3]:  # Log first 3 issues
                    self.logger.warning(f"  - {issue['description']}")

        except Exception as e:
            self.logger.error(f"Failed to log system summary: {e}")

    async def _save_system_status(self, summary: Dict[str, Any]):
        """Save system status to file."""
        try:
            with open(self.status_file, "w") as f:
                json.dump(summary, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save system status: {e}")

    async def _send_status_updates(self):
        """Send status updates to other agents."""
        try:
            # Send our status
            await self.message_bus.broadcast(
                sender=self.agent_name,
                message_type=MessageType.STATUS_UPDATE,
                content={
                    "agent_name": self.agent_name,
                    "status": "running" if self.running else "stopped",
                    "health": self.health_status,
                    "timestamp": datetime.now().isoformat(),
                    "message_count": len(self.message_history),
                    "active_issues": len(self.issues_detected),
                },
                priority=MessagePriority.NORMAL,
            )

        except Exception as e:
            self.logger.error(f"Failed to send status update: {e}")

    async def _handle_user_notifications(self):
        """Handle user notifications and alerts."""
        # In a real implementation, you'd check for user notifications
        # and send them through appropriate channels (email, webhook, etc.)
        pass

    def _cleanup_old_data(self):
        """Clean up old data to prevent memory bloat."""
        current_time = datetime.now()

        # Clean up old messages (keep last 1000)
        if len(self.message_history) > 1000:
            self.message_history = self.message_history[-1000:]

        # Clean up old notifications (keep last 100)
        if len(self.user_notifications) > 100:
            self.user_notifications = self.user_notifications[-100:]

        # Clean up old system health history (keep last 24 hours)
        cutoff_time = current_time - timedelta(hours=24)
        self.system_health_history = [
            summary
            for summary in self.system_health_history
            if datetime.fromisoformat(summary.get("timestamp", "1970-01-01"))
            > cutoff_time
        ]

    async def _setup_subscriptions(self):
        """Set up message subscriptions for the communicator."""
        await super()._setup_subscriptions()

        # Subscribe to all message types for logging
        for message_type in MessageType:
            await self.message_bus.subscribe(message_type, self._handle_message)
            self.subscribed_message_types.append(message_type)

    async def _handle_message(self, message):
        """Handle all incoming messages for logging."""
        if message.sender == self.agent_name:
            return  # Ignore our own messages

        # Store message for history
        message_record = {
            "timestamp": datetime.now().isoformat(),
            "sender": message.sender,
            "type": message.type.value,
            "priority": message.priority.value,
            "content": message.content,
        }

        self.message_history.append(message_record)

        # Log important messages
        if message.priority in [
            MessagePriority.HIGH,
            MessagePriority.CRITICAL,
            MessagePriority.EMERGENCY,
        ]:
            self.logger.warning(
                f"High priority message from {message.sender}: {message.type.value}"
            )

        # Handle specific message types
        if message.type == MessageType.ALERT:
            await self._handle_alert_message(message)
        elif message.type == MessageType.REMEDIATION_RESULT:
            await self._handle_remediation_result(message)
        elif message.type == MessageType.HEALTH_CHECK:
            await self._handle_health_check(message)
        elif message.type == MessageType.SYSTEM_COMMAND:
            # Broadcast a visible message for command receipt
            await self.message_bus.broadcast(
                sender=self.agent_name,
                message_type=MessageType.COORDINATION,
                content={
                    "info": f"{self.agent_name} received system command: {message.content.get('command', 'unknown')}"
                },
                priority=MessagePriority.NORMAL,
            )

    async def _handle_alert_message(self, message):
        """Handle alert messages."""
        alert_content = message.content
        severity = alert_content.get("severity", "medium")
        alert_message = alert_content.get("message", "Unknown alert")
        alert_type = alert_content.get("type", "")

        if alert_type == "llm_quota_cleared":
            self.clear_llm_quota_alert()
            self.logger.info(
                "LLM quota alert cleared. System will resume normal LLM usage."
            )
            self.add_user_notification(
                alert_message, notification_type="info", severity="info"
            )
            return

        if severity in ["critical", "high"]:
            self.logger.critical(f"🚨 CRITICAL ALERT: {alert_message}")

            # Add to user notifications
            self.user_notifications.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "type": "critical_alert",
                    "message": alert_message,
                    "severity": severity,
                }
            )
            # If this is an LLM quota alert, set a persistent flag
            if alert_type == "llm_quota_exceeded":
                self.llm_quota_alert_active = True
                self.llm_quota_alert_message = alert_message
        else:
            self.logger.warning(f"⚠️ Alert: {alert_message}")

    async def _handle_remediation_result(self, message):
        """Handle remediation result messages."""
        result_content = message.content
        success = result_content.get("success", False)
        action = result_content.get("action", "Unknown action")
        target = result_content.get("target", "Unknown target")

        if success:
            self.logger.success(f"✅ Remediation successful: {action} on {target}")
        else:
            self.logger.error(f"❌ Remediation failed: {action} on {target}")

    async def _handle_health_check(self, message):
        """Handle health check messages."""
        health_content = message.content
        agent_name = health_content.get("agent_name", "Unknown")
        status = health_content.get("status", "unknown")

        # Update agent status
        self.agent_status[agent_name] = health_content

        if status == "critical":
            self.logger.error(f"Agent {agent_name} is in critical condition")
        elif status == "warning":
            self.logger.warning(f"Agent {agent_name} is showing warning signs")

    def get_communication_summary(self) -> Dict[str, Any]:
        """Get a summary of communication activities."""
        return {
            "total_messages_processed": len(self.message_history),
            "agent_status_count": len(self.agent_status),
            "system_summaries_generated": len(self.system_health_history),
            "user_notifications": len(self.user_notifications),
            "active_issues": len(self.issues_detected),
            "recent_messages": (
                [
                    {
                        "timestamp": msg.get("timestamp", "unknown"),
                        "description": msg.get("description")
                        or f"Message from {msg.get('sender', 'unknown')}: {msg.get('type', 'unknown')}",
                    }
                    for msg in self.message_history[-10:]
                ]
                if self.message_history
                else []
            ),
            "system_health_file": self.status_file,
        }

    def add_user_notification(
        self, message: str, notification_type: str = "info", severity: str = "medium"
    ):
        """Add a user notification."""
        notification = {
            "timestamp": datetime.now().isoformat(),
            "type": notification_type,
            "message": message,
            "severity": severity,
        }

        self.user_notifications.append(notification)
        self.logger.info(f"User notification added: {message}")

    def get_system_status(self) -> Optional[Dict[str, Any]]:
        """Get the current system status."""
        if self.system_health_history:
            return self.system_health_history[-1]
        return None

    def clear_llm_quota_alert(self):
        self.llm_quota_alert_active = False
        self.llm_quota_alert_message = None
