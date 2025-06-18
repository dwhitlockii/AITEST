from abc import ABC, abstractmethod
from typing import Any, Dict


class BasePlugin(ABC):
    """
    Base class for all system plugins.
    Plugins must subclass this and implement required methods.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    @abstractmethod
    def register(self, system_context: Dict[str, Any]):
        """
        Register the plugin with the system.
        system_context provides orchestrator, config, message_bus, etc.
        """
        pass

    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """
        Return the plugin's configuration dictionary.
        """
        pass
