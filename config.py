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
    cpu_warning: float = 75.0   # CPU usage % that raises eyebrows
    memory_critical: float = 95.0  # Memory usage % that makes us sweat
    memory_warning: float = 85.0   # Memory usage % that gets our attention
    disk_critical: float = 95.0    # Disk usage % that's basically full
    disk_warning: float = 85.0     # Disk usage % that needs attention
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
class GPTConfig:
    """GPT API configuration - the brain behind the operation."""
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    model: str = "gpt-4"
    max_tokens: int = 500
    temperature: float = 0.3  # Lower for more consistent decisions
    timeout: int = 30
    retry_attempts: int = 3  # Number of retry attempts for GPT API
    retry_delay: int = 2    # Delay (seconds) between retries

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
                "spooler", "themes", "wsearch", "wuauserv",  # Windows services
                "explorer", "svchost", "winlogon"  # Critical processes
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

class Config:
    """Main configuration class - the command center for all settings."""
    
    def __init__(self):
        self.thresholds = SystemThresholds()
        self.gpt = GPTConfig()
        self.monitoring = MonitoringConfig()
        self.logging = LoggingConfig()
        
        # Agent configurations - each with their own personality
        self.agents = {
            "sensor": AgentConfig(
                name="SensorAgent",
                description="The eyes and ears of the system - gathers all the metrics",
                check_interval=5.0,  # Check every 5 seconds
                enabled=True
            ),
            "analyzer": AgentConfig(
                name="AnalyzerAgent", 
                description="The brain that spots trouble before it becomes a disaster",
                check_interval=10.0,  # Analyze every 10 seconds
                enabled=True
            ),
            "remediator": AgentConfig(
                name="RemediatorAgent",
                description="The fixer - when things break, this agent makes them work again",
                check_interval=15.0,  # Remediate every 15 seconds
                enabled=True,
                max_concurrent_actions=1  # Be careful with fixes
            ),
            "communicator": AgentConfig(
                name="CommunicatorAgent",
                description="The mouthpiece - keeps everyone informed and logs everything",
                check_interval=2.0,  # Communicate frequently
                enabled=True
            )
        }
        
        # LLM provider for each agent
        self.agent_ai_provider = {
            "analyzer": "openai",
            "remediator": "gemini"
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
        
    def get_agent_config(self, agent_name: str) -> AgentConfig:
        """Get configuration for a specific agent."""
        return self.agents.get(agent_name)
    
    def update_threshold(self, metric: str, value: float):
        """Dynamically update thresholds - for when we need to adapt."""
        if hasattr(self.thresholds, metric):
            setattr(self.thresholds, metric, value)
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {
            "thresholds": self.thresholds.__dict__,
            "gpt": self.gpt.__dict__,
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
            "fallback_mode_on_llm_quota_exceeded": self.fallback_mode_on_llm_quota_exceeded
        }

# Global configuration instance
config = Config() 