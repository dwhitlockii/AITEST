"""
Logging utility for the multi-agent monitoring system.
Because every good system needs to know what it's doing, and we want it to look pretty too.
"""

import logging
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme
from rich.panel import Panel
from rich.text import Text
import colorama
from colorama import Fore, Back, Style

from config import config

# Initialize colorama for Windows compatibility
colorama.init()


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log messages - because why not make it pretty?"""

    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.RED + Back.WHITE + Style.BRIGHT,
    }

    def format(self, record):
        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Get color for log level
        color = self.COLORS.get(record.levelname, Fore.WHITE)

        # Format the message
        formatted = f"{Fore.BLUE}[{timestamp}]{Style.RESET_ALL} "
        formatted += f"{color}[{record.levelname:8}]{Style.RESET_ALL} "
        formatted += f"{Fore.MAGENTA}[{record.name}]{Style.RESET_ALL} "
        formatted += f"{record.getMessage()}"

        return formatted


class SystemLogger:
    """
    Enhanced logging system with personality, colors, and Windows compatibility.
    Provides verbose, insightful, and occasionally cheeky logs for the multi-agent system.
    """

    def __init__(
        self, name: str = "AgentSystem", log_file: str = "debug_output/agent_system.log"
    ):
        self.name = name
        self.log_file = log_file

        # Create debug output directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # Configure rich console with custom theme
        self.console = Console(
            theme=Theme(
                {
                    "info": "cyan",
                    "warning": "yellow",
                    "error": "red",
                    "critical": "red bold",
                    "success": "green",
                    "agent": "blue",
                    "system": "magenta",
                    "gpt": "bright_blue",
                    "metric": "bright_green",
                    "alert": "bright_red",
                    "remediation": "bright_yellow",
                }
            )
        )

        # Configure logging
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Clear existing handlers
        self.logger.handlers.clear()

        # Console handler with Rich formatting
        console_handler = RichHandler(
            console=self.console, show_time=True, show_path=False, markup=True
        )
        console_handler.setLevel(logging.WARNING)
        self.logger.addHandler(console_handler)

        # File handler with UTF-8 encoding for Windows compatibility
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.WARNING)

        # Create formatter for file logging
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Set Windows console encoding if on Windows
        if sys.platform == "win32":
            try:
                # Try to set console to UTF-8
                os.system("chcp 65001 > nul")
            except:
                pass  # Fallback if chcp fails

    def _get_personality_prefix(self, level: str) -> str:
        """Get personality-infused prefix based on log level."""
        prefixes = {
            "info": "🔍",
            "warning": "⚠️",
            "error": "💥",
            "critical": "🚨",
            "success": "✅",
            "debug": "🔧",
        }
        return prefixes.get(level, "📝")

    def _get_agent_emoji(self, agent_name: str) -> str:
        """Get appropriate emoji for different agent types."""
        emoji_map = {
            "sensor": "📡",
            "analyzer": "🧠",
            "remediator": "🔧",
            "communicator": "📢",
            "orchestrator": "🎭",
            "messagebus": "📨",
        }

        agent_lower = agent_name.lower()
        for key, emoji in emoji_map.items():
            if key in agent_lower:
                return emoji
        return "🤖"

    def info(self, message: str, **kwargs):
        """Log info message with personality."""
        prefix = self._get_personality_prefix("info")
        self.logger.info(f"{prefix} {message}", **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with personality."""
        prefix = self._get_personality_prefix("warning")
        self.logger.warning(f"{prefix} {message}", **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message with personality."""
        prefix = self._get_personality_prefix("error")
        self.logger.error(f"{prefix} {message}", **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message with personality."""
        prefix = self._get_personality_prefix("critical")
        self.logger.critical(f"{prefix} {message}", **kwargs)

    def success(self, message: str, **kwargs):
        """Log success message with personality."""
        prefix = self._get_personality_prefix("success")
        self.logger.info(f"{prefix} {message}", **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message with personality."""
        prefix = self._get_personality_prefix("debug")
        self.logger.debug(f"{prefix} {message}", **kwargs)

    def agent_info(self, agent_name: str, message: str, **kwargs):
        """Log agent-specific info message."""
        emoji = self._get_agent_emoji(agent_name)
        self.logger.info(f"{emoji} {agent_name}: {message}", **kwargs)

    def agent_warning(self, agent_name: str, message: str, **kwargs):
        """Log agent-specific warning message."""
        emoji = self._get_agent_emoji(agent_name)
        self.logger.warning(f"{emoji} {agent_name}: {message}", **kwargs)

    def agent_error(self, agent_name: str, message: str, **kwargs):
        """Log agent-specific error message."""
        emoji = self._get_agent_emoji(agent_name)
        self.logger.error(f"{emoji} {agent_name}: {message}", **kwargs)

    def system_startup(self, message: str, **kwargs):
        """Log system startup message."""
        self.logger.info(f"🚀 SYSTEM STARTUP: {message}", **kwargs)

    def system_shutdown(self, message: str, **kwargs):
        """Log system shutdown message."""
        self.logger.info(f"🛑 SYSTEM SHUTDOWN: {message}", **kwargs)

    def gpt_request(self, message: str, **kwargs):
        """Log GPT API request."""
        self.logger.info(f"🤖 GPT REQUEST: {message}", **kwargs)

    def gpt_response(self, message: str, **kwargs):
        """Log GPT API response."""
        self.logger.info(f"🧠 GPT RESPONSE: {message}", **kwargs)

    def metric_alert(self, metric: str, value: float, threshold: float, **kwargs):
        """Log metric alert."""
        self.logger.warning(
            f"📊 METRIC ALERT: {metric} = {value} (threshold: {threshold})", **kwargs
        )

    def remediation_action(self, action: str, target: str, **kwargs):
        """Log remediation action."""
        self.logger.info(f"🔧 REMEDIATION: {action} on {target}", **kwargs)

    def metric(
        self, metric_name: str, value: Any, threshold: Optional[float] = None, **kwargs
    ):
        """Log a metric with optional threshold comparison."""
        if threshold:
            status = "🟢" if value <= threshold else "🔴"
            self.logger.info(
                f"📊 {metric_name}: {value} (threshold: {threshold}) {status}", **kwargs
            )
        else:
            self.logger.info(f"📊 {metric_name}: {value}", **kwargs)

    def action(self, action: str, target: str, result: str = "initiated", **kwargs):
        """Log an agent action."""
        self.logger.info(f"🎯 {action} on {target} - {result}", **kwargs)

    def gpt_decision(self, decision: str, reasoning: str, **kwargs):
        """Log a GPT-based decision."""
        self.logger.info(
            f"🧠 GPT Decision: {decision} | Reasoning: {reasoning}", **kwargs
        )

    def health_check(self, status: str, details: Dict[str, Any], **kwargs):
        """Log system health status."""
        status_emoji = (
            "🟢" if status == "healthy" else "🔴" if status == "critical" else "🟡"
        )
        self.logger.info(f"{status_emoji} HEALTH CHECK: {status} - {details}", **kwargs)

    def startup(self, message: str, **kwargs):
        """Log startup message."""
        self.system_startup(message, **kwargs)

    def shutdown(self, message: str, **kwargs):
        """Log shutdown message."""
        self.system_shutdown(message, **kwargs)


# Global logger instance
system_logger = SystemLogger()


# Agent-specific logger class
class AgentLogger:
    """Logger wrapper for individual agents with personality."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = system_logger.logger

    def info(self, message: str, **kwargs):
        """Log info message for this agent."""
        emoji = system_logger._get_agent_emoji(self.agent_name)
        self.logger.info(f"{emoji} {self.agent_name}: {message}", **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message for this agent."""
        emoji = system_logger._get_agent_emoji(self.agent_name)
        self.logger.warning(f"{emoji} {self.agent_name}: {message}", **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message for this agent."""
        emoji = system_logger._get_agent_emoji(self.agent_name)
        self.logger.error(f"{emoji} {self.agent_name}: {message}", **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message for this agent."""
        emoji = system_logger._get_agent_emoji(self.agent_name)
        self.logger.debug(f"{emoji} {self.agent_name}: {message}", **kwargs)

    def success(self, message: str, **kwargs):
        """Log success message for this agent."""
        emoji = system_logger._get_agent_emoji(self.agent_name)
        self.logger.info(f"{emoji} {self.agent_name}: ✅ {message}", **kwargs)

    def remediation_action(self, action: str, target: str, **kwargs):
        """Log remediation action."""
        self.logger.info(f"🔧 REMEDIATION: {action} on {target}", **kwargs)

    def metric(
        self, metric_name: str, value: Any, threshold: Optional[float] = None, **kwargs
    ):
        """Log a metric with optional threshold comparison."""
        emoji = system_logger._get_agent_emoji(self.agent_name)
        if threshold:
            status = "🟢" if value <= threshold else "🔴"
            self.logger.info(
                f"{emoji} {self.agent_name}: 📊 {metric_name}: {value} (threshold: {threshold}) {status}",
                **kwargs,
            )
        else:
            self.logger.info(
                f"{emoji} {self.agent_name}: 📊 {metric_name}: {value}", **kwargs
            )

    def action(self, action: str, target: str, result: str = "initiated", **kwargs):
        """Log an agent action."""
        emoji = system_logger._get_agent_emoji(self.agent_name)
        self.logger.info(
            f"{emoji} {self.agent_name}: 🎯 {action} on {target} - {result}", **kwargs
        )

    def gpt_decision(self, decision: str, reasoning: str, **kwargs):
        """Log a GPT-based decision."""
        emoji = system_logger._get_agent_emoji(self.agent_name)
        self.logger.info(
            f"{emoji} {self.agent_name}: 🧠 GPT Decision: {decision} | Reasoning: {reasoning}",
            **kwargs,
        )

    def health_check(self, status: str, details: Dict[str, Any], **kwargs):
        """Log system health status."""
        status_emoji = (
            "🟢" if status == "healthy" else "🔴" if status == "critical" else "🟡"
        )
        self.logger.info(f"{status_emoji} HEALTH CHECK: {status} - {details}", **kwargs)

    def startup(self, message: str, **kwargs):
        """Log startup message."""
        self.system_startup(message, **kwargs)

    def shutdown(self, message: str, **kwargs):
        """Log shutdown message."""
        self.system_shutdown(message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message for this agent."""
        emoji = system_logger._get_agent_emoji(self.agent_name)
        self.logger.critical(f"{emoji} {self.agent_name}: CRITICAL: {message}", **kwargs)


def create_agent_logger(agent_name: str) -> AgentLogger:
    """Factory function to create agent loggers."""
    return AgentLogger(agent_name)


def create_system_logger() -> SystemLogger:
    """Factory function to create system logger."""
    return SystemLogger()


# Global loggers
system_logger = create_system_logger()
