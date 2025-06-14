# ABOUTME: Plugin registry system for dynamic plugin discovery, loading, and management
# ABOUTME: Handles plugin lifecycle, dependencies, and provides plugin access interface

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Any

from app.plugins.base import BasePlugin

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Central registry for managing plugins."""

    def __init__(self):
        """Initialize the plugin registry."""
        self._plugins: dict[str, BasePlugin] = {}
        self._plugin_classes: dict[str, type[BasePlugin]] = {}
        self._plugin_configs: dict[str, dict[str, Any]] = {}
        self._initialized = False

    def initialize(self, plugin_config: dict[str, Any] | None = None) -> None:
        """Initialize the plugin registry and load plugins.

        Args:
            plugin_config: Configuration for plugins
        """
        if self._initialized:
            logger.warning("Plugin registry already initialized")
            return

        self._plugin_configs = plugin_config or {}

        # Discover and load plugins
        self._discover_plugins()
        self._load_plugins()

        self._initialized = True
        logger.info(f"Plugin registry initialized with {len(self._plugins)} plugins")

    def _discover_plugins(self) -> None:
        """Discover available plugins in the plugins directory."""
        plugins_dir = Path(__file__).parent

        # Discover Python modules in plugins directory
        for plugin_file in plugins_dir.glob("*.py"):
            if plugin_file.name.startswith("_") or plugin_file.name in [
                "base.py",
                "registry.py",
            ]:
                continue

            module_name = plugin_file.stem
            self._load_plugin_module(module_name, plugin_file)

        # Discover plugins in subdirectories
        for plugin_dir in plugins_dir.iterdir():
            if plugin_dir.is_dir() and not plugin_dir.name.startswith("_"):
                self._discover_plugins_in_directory(plugin_dir)

    def _discover_plugins_in_directory(self, plugin_dir: Path) -> None:
        """Discover plugins in a specific directory."""
        init_file = plugin_dir / "__init__.py"
        if init_file.exists():
            module_name = f"{plugin_dir.name}"
            self._load_plugin_module(module_name, init_file)

        # Also check for individual plugin files in the directory
        for plugin_file in plugin_dir.glob("*.py"):
            if not plugin_file.name.startswith("_"):
                module_name = f"{plugin_dir.name}.{plugin_file.stem}"
                self._load_plugin_module(module_name, plugin_file)

    def _load_plugin_module(self, module_name: str, module_path: Path) -> None:
        """Load a plugin module and extract plugin classes."""
        try:
            spec = importlib.util.spec_from_file_location(
                f"app.plugins.{module_name}", module_path
            )
            if spec is None or spec.loader is None:
                logger.warning(f"Could not load plugin module: {module_name}")
                return

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find plugin classes in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                if (
                    isinstance(attr, type)
                    and issubclass(attr, BasePlugin)
                    and attr != BasePlugin
                    and not attr.__name__.startswith("Base")
                ):
                    plugin_name = attr.__name__
                    self._plugin_classes[plugin_name] = attr
                    logger.debug(f"Discovered plugin class: {plugin_name}")

        except Exception as e:
            logger.error(f"Error loading plugin module {module_name}: {e}")

    def _load_plugins(self) -> None:
        """Load and initialize discovered plugins."""
        for plugin_name, plugin_class in self._plugin_classes.items():
            try:
                # Get plugin configuration
                plugin_config = self._plugin_configs.get(plugin_name, {})

                # Skip disabled plugins
                if not plugin_config.get("enabled", True):
                    logger.info(f"Skipping disabled plugin: {plugin_name}")
                    continue

                # Instantiate plugin
                plugin = plugin_class(plugin_config)

                # Initialize plugin
                plugin.initialize()

                # Store in registry
                self._plugins[plugin_name] = plugin
                logger.info(f"Loaded plugin: {plugin_name} v{plugin.version}")

            except Exception as e:
                logger.error(f"Error loading plugin {plugin_name}: {e}")

    def get_plugin(self, plugin_name: str) -> BasePlugin | None:
        """Get a plugin by name.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin instance or None if not found
        """
        return self._plugins.get(plugin_name)

    def get_plugins_by_type(self, plugin_type: str) -> list[BasePlugin]:
        """Get all plugins of a specific type.

        Args:
            plugin_type: Type of plugins to retrieve

        Returns:
            List of plugin instances
        """
        return [
            plugin
            for plugin in self._plugins.values()
            if plugin.plugin_type == plugin_type and plugin.is_enabled()
        ]

    def list_plugins(self) -> dict[str, dict[str, Any]]:
        """List all registered plugins with their information.

        Returns:
            Dictionary of plugin information
        """
        return {name: plugin.get_info() for name, plugin in self._plugins.items()}

    def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a plugin.

        Args:
            plugin_name: Name of the plugin to enable

        Returns:
            True if plugin was enabled, False otherwise
        """
        plugin = self.get_plugin(plugin_name)
        if plugin:
            plugin.enable()
            return True
        return False

    def disable_plugin(self, plugin_name: str) -> bool:
        """Disable a plugin.

        Args:
            plugin_name: Name of the plugin to disable

        Returns:
            True if plugin was disabled, False otherwise
        """
        plugin = self.get_plugin(plugin_name)
        if plugin:
            plugin.disable()
            return True
        return False

    def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a plugin.

        Args:
            plugin_name: Name of the plugin to reload

        Returns:
            True if plugin was reloaded, False otherwise
        """
        try:
            # Get plugin class
            plugin_class = self._plugin_classes.get(plugin_name)
            if not plugin_class:
                logger.error(f"Plugin class not found: {plugin_name}")
                return False

            # Cleanup old plugin
            old_plugin = self._plugins.get(plugin_name)
            if old_plugin:
                old_plugin.cleanup()

            # Create new plugin instance
            plugin_config = self._plugin_configs.get(plugin_name, {})
            new_plugin = plugin_class(plugin_config)
            new_plugin.initialize()

            # Update registry
            self._plugins[plugin_name] = new_plugin

            logger.info(f"Reloaded plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Error reloading plugin {plugin_name}: {e}")
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin.

        Args:
            plugin_name: Name of the plugin to unload

        Returns:
            True if plugin was unloaded, False otherwise
        """
        try:
            plugin = self._plugins.get(plugin_name)
            if plugin:
                plugin.cleanup()
                del self._plugins[plugin_name]
                logger.info(f"Unloaded plugin: {plugin_name}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_name}: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up all plugins and the registry."""
        for plugin_name, plugin in self._plugins.items():
            try:
                plugin.cleanup()
                logger.debug(f"Cleaned up plugin: {plugin_name}")
            except Exception as e:
                logger.error(f"Error cleaning up plugin {plugin_name}: {e}")

        self._plugins.clear()
        self._plugin_classes.clear()
        self._plugin_configs.clear()
        self._initialized = False

        logger.info("Plugin registry cleaned up")


# Global plugin registry instance
plugin_registry = PluginRegistry()


def get_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry instance."""
    return plugin_registry


def get_plugin(plugin_name: str) -> BasePlugin | None:
    """Convenience function to get a plugin by name."""
    return plugin_registry.get_plugin(plugin_name)


def get_plugins_by_type(plugin_type: str) -> list[BasePlugin]:
    """Convenience function to get plugins by type."""
    return plugin_registry.get_plugins_by_type(plugin_type)


def initialize_plugins(plugin_config: dict[str, Any] | None = None) -> None:
    """Initialize the plugin system."""
    plugin_registry.initialize(plugin_config)
