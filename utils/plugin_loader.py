import importlib
import os
import sys
from typing import List, Dict, Any
from plugins.base_plugin import BasePlugin


def load_plugins(config, system_context: Dict[str, Any]) -> List[BasePlugin]:
    """
    Load and register plugins as specified in config.plugins_to_load.
    Returns a list of loaded plugin instances.
    """
    plugins_dir = os.path.join(os.path.dirname(__file__), "..", "plugins")
    plugins_dir = os.path.abspath(plugins_dir)
    if plugins_dir not in sys.path:
        sys.path.insert(0, plugins_dir)

    loaded_plugins = []
    plugins_to_load = getattr(config, "plugins_to_load", [])
    plugins_enabled = getattr(config, "plugins_enabled", True)
    if not plugins_enabled or not plugins_to_load:
        return loaded_plugins

    for plugin_name in plugins_to_load:
        try:
            module = importlib.import_module(f"plugins.{plugin_name}")
            # Find a class that subclasses BasePlugin
            plugin_class = None
            for attr in dir(module):
                obj = getattr(module, attr)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BasePlugin)
                    and obj is not BasePlugin
                ):
                    plugin_class = obj
                    break
            if not plugin_class:
                print(f"[PluginLoader] No BasePlugin subclass found in {plugin_name}")
                continue
            # Instantiate and register
            plugin_config = getattr(config, "plugin_configs", {}).get(plugin_name, {})
            plugin_instance = plugin_class(plugin_config)
            plugin_instance.register(system_context)
            loaded_plugins.append(plugin_instance)
            print(f"[PluginLoader] Loaded plugin: {plugin_name}")
        except Exception as e:
            print(f"[PluginLoader] Failed to load plugin {plugin_name}: {e}")
    return loaded_plugins
