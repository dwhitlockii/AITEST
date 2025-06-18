"""
Configuration module for the GPT-driven multi-agent monitoring system.
Think of this as the control room dashboard - everything centralized and tweakable.
"""

import os
from typing import Dict, Any, List
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class SystemThresholds:
    """System health thresholds - the red lines we don't want to cross."""

    cpu_critical: float = 90.0  # CPU usage % that triggers panic mode
    cpu_warning: float = 75.0  # CPU usage % that raises eyebrows
    memory_critical: float = 95.0  # Memory usage % that makes us sweat
    memory_warning: float = 85.0  # Memory usage % that gets our attention
    disk_critical: float = 95.0  # Disk usage % that's basically full
    disk_warning: float = 85.0  # Disk usage % that needs attention
    service_restart_attempts: int = 3  # How many times to try restarting a service


@dataclass
class AgentConfig:
    """Individual agent configuration - each agent's personality and capabilities."""

    name: str
    description: str
    check_interval: float  # seconds between checks
    enabled: bool = True
    max_concurrent_actions: int = 2
    escalation_threshold: int = 3  # failures before escalating


@dataclass
class MonitoringConfig:
    """What we're actually monitoring - the targets of our surveillance."""

    services_to_monitor: List[str] = None
    disk_paths: List[str] = None
    network_interfaces: List[str] = None

    def __post_init__(self):
        if self.services_to_monitor is None:
            # Default services that are usually important
            self.services_to_monitor = [
                "spooler",
                "themes",
                "wsearch",
                "wuauserv",  # Windows services
                "explorer",
                "svchost",
                "winlogon",  # Critical processes
            ]

        if self.disk_paths is None:
            self.disk_paths = ["C:\\"]  # Monitor C: drive by default

        if self.network_interfaces is None:
            self.network_interfaces = ["Ethernet", "Wi-Fi"]


@dataclass
class LoggingConfig:
    """Logging configuration - because we need to know what's happening."""

    log_level: str = "INFO"
    log_file: str = "debug_output/agent_system.log"
    max_log_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True
    file_output: bool = True


@dataclass
class OllamaConfig:
    """Ollama local LLM configuration - for API key-free LLM communication."""

    url: str = "http://localhost:11434"
    model: str = "llama2:latest"
    timeout: int = 60  # Increased from 30 to 60 seconds for better reliability
    retry_attempts: int = 3
    retry_delay: int = 2
    enabled: bool = True


class Config:
    """
    Central configuration for the monitoring system.
    NOTE: This system is now Ollama-only for LLM operations. No OpenAI or Gemini support.
    All LLM-using agents will use Ollama (local, API key-free) exclusively.

    persistence_enabled: Enable/disable database persistence (default: True)
    db_path: Path to SQLite database file (default: 'data/agent_system.db')
    browser_cache_cleanup_enabled: Enable/disable browser cache cleanup remediation (default: True)
    user_process_restart_enabled: Enable/disable user process restart remediation (default: True)
    temp_cleanup_enabled: Enable/disable Windows temp directory cleanup (default: True)
    dns_flush_enabled: Enable/disable DNS cache flush remediation (default: True)
    network_reset_enabled: Enable/disable network adapter reset remediation (default: True)
    plugins_enabled: Enable/disable plugin system (default: True)
    plugins_to_load: List of plugin module names to load (default: empty)
    plugin_configs: Dict of plugin-specific configs (default: empty)
    """

    def __init__(self):
        self.thresholds = SystemThresholds()
        self.monitoring = MonitoringConfig()
        self.logging = LoggingConfig()

        # Agent configurations
        self.agents = {
            "sensor": AgentConfig(
                name="SensorAgent",
                description="Collects system metrics",
                check_interval=10.0,
                enabled=True,
            ),
            "analyzer": AgentConfig(
                name="AnalyzerAgent",
                description="Analyzes metrics using LLM",
                check_interval=60.0,
                enabled=True,
            ),
            "remediator": AgentConfig(
                name="RemediatorAgent",
                description="Performs remediation actions",
                check_interval=60.0,
                enabled=True,
            ),
            "communicator": AgentConfig(
                name="CommunicatorAgent",
                description="Handles logging and communication",
                check_interval=15.0,
                enabled=True,
            ),
            "security": AgentConfig(
                name="SecurityAgent",
                description="Monitors security events",
                check_interval=45.0,
                enabled=True,
            ),
            "network": AgentConfig(
                name="NetworkAgent",
                description="Monitors network performance",
                check_interval=45.0,
                enabled=True,
            ),
            "application": AgentConfig(
                name="ApplicationAgent",
                description="Monitors application performance",
                check_interval=60.0,
                enabled=True,
            ),
            "compliance": AgentConfig(
                name="ComplianceAgent",
                description="Monitors compliance and policy",
                check_interval=90.0,
                enabled=True,
            ),
            "backup": AgentConfig(
                name="BackupAgent",
                description="Monitors backup and disaster recovery",
                check_interval=120.0,
                enabled=True,
            ),
            "predictive": AgentConfig(
                name="PredictiveAgent",
                description="Performs predictive analysis",
                check_interval=120.0,
                enabled=True,
            ),
        }

        # Force all LLM-using agents to use Ollama by default
        self.agent_ai_provider = {
            "analyzer": "ollama",
            "remediator": "ollama",
        }

        # Message queue configuration
        self.message_queue_size = 1000
        self.message_retention_time = 300  # 5 minutes

        # Self-healing configuration
        self.auto_healing_enabled = True
        self.healing_cooldown = 60  # seconds between healing attempts
        self.max_healing_attempts_per_issue = 3

        # Web interface configuration
        self.web_interface_enabled = True
        self.web_port = 8000
        self.web_host = "0.0.0.0"
        # Fallback mode config: if True, go straight to rule-based fallback on LLM quota exceeded
        # If False, try Gemini first, then fallback
        self.fallback_mode_on_llm_quota_exceeded = True

        # Persistence configuration
        self.persistence_enabled = True
        self.db_path = "data/agent_system.db"
        # Remediation action toggles
        self.browser_cache_cleanup_enabled = True
        self.user_process_restart_enabled = True
        self.temp_cleanup_enabled = True
        self.dns_flush_enabled = True
        self.network_reset_enabled = True

        # Plugin system configuration
        self.plugins_enabled = True
        self.plugins_to_load = ['sample_remediation_plugin']
        self.plugin_configs = {
            'sample_remediation_plugin': {'enabled': True}
        }

        # LLM fallback state
        self.llm_fallback_active = False  # True if OpenAI quota exceeded and fallback is required
        self.llm_fallback_reason = None

        # Ollama configuration
        self.ollama = OllamaConfig()

    def get_agent_config(self, agent_name: str) -> AgentConfig:
        """Get configuration for a specific agent."""
        return self.agents.get(agent_name)

    def update_threshold(self, metric: str, value: float):
        """Dynamically update thresholds - for when we need to adapt."""
        if hasattr(self.thresholds, metric):
            setattr(self.thresholds, metric, value)
            return True
        return False

    def activate_llm_fallback(self, reason: str = None):
        self.llm_fallback_active = True
        self.llm_fallback_reason = reason or "OpenAI quota exceeded"

    def clear_llm_fallback(self):
        self.llm_fallback_active = False
        self.llm_fallback_reason = None

    def is_llm_fallback_active(self) -> bool:
        return self.llm_fallback_active

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {
            "thresholds": self.thresholds.__dict__,
            "ollama": self.ollama.__dict__,
            "monitoring": self.monitoring.__dict__,
            "logging": self.logging.__dict__,
            "agents": {k: v.__dict__ for k, v in self.agents.items()},
            "message_queue_size": self.message_queue_size,
            "message_retention_time": self.message_retention_time,
            "auto_healing_enabled": self.auto_healing_enabled,
            "healing_cooldown": self.healing_cooldown,
            "max_healing_attempts_per_issue": self.max_healing_attempts_per_issue,
            "web_interface_enabled": self.web_interface_enabled,
            "web_port": self.web_port,
            "web_host": self.web_host,
            "fallback_mode_on_llm_quota_exceeded": self.fallback_mode_on_llm_quota_exceeded,
            "persistence_enabled": self.persistence_enabled,
            "db_path": self.db_path,
            "browser_cache_cleanup_enabled": self.browser_cache_cleanup_enabled,
            "user_process_restart_enabled": self.user_process_restart_enabled,
            "temp_cleanup_enabled": self.temp_cleanup_enabled,
            "dns_flush_enabled": self.dns_flush_enabled,
            "network_reset_enabled": self.network_reset_enabled,
            "plugins_enabled": self.plugins_enabled,
            "plugins_to_load": self.plugins_to_load,
            "plugin_configs": self.plugin_configs,
            "llm_fallback_active": self.llm_fallback_active,
            "llm_fallback_reason": self.llm_fallback_reason,
        }

    def _load_env_vars(self):
        """Load configuration from environment variables."""
        # Ollama settings
        if os.getenv("OLLAMA_URL"):
            self.ollama.url = os.getenv("OLLAMA_URL")
        if os.getenv("OLLAMA_MODEL"):
            self.ollama.model = os.getenv("OLLAMA_MODEL")
        if os.getenv("OLLAMA_ENABLED"):
            self.ollama.enabled = os.getenv("OLLAMA_ENABLED").lower() == "true"

        # Agent provider preferences
        if os.getenv("ANALYZER_AI_PROVIDER"):
            self.agent_ai_provider["analyzer"] = os.getenv("ANALYZER_AI_PROVIDER")
        if os.getenv("REMEDIATOR_AI_PROVIDER"):
            self.agent_ai_provider["remediator"] = os.getenv("REMEDIATOR_AI_PROVIDER")

        # Persistence settings
        if os.getenv("PERSISTENCE_ENABLED"):
            self.persistence_enabled = os.getenv("PERSISTENCE_ENABLED").lower() == "true"
        if os.getenv("DB_PATH"):
            self.db_path = os.getenv("DB_PATH")


# Global configuration instance
config = Config()
