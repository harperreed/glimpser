# ABOUTME: Base plugin interfaces and abstract classes for the plugin system
# ABOUTME: Defines contracts that all plugins must implement for consistent behavior

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class PluginError(Exception):
    """Base exception for plugin-related errors."""


class PluginConfigError(PluginError):
    """Raised when plugin configuration is invalid."""


class PluginExecutionError(PluginError):
    """Raised when plugin execution fails."""


class BasePlugin(ABC):
    """Abstract base class that all plugins must inherit from."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the plugin with optional configuration.

        Args:
            config: Plugin-specific configuration dictionary
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.name = self.__class__.__name__
        self.logger = logging.getLogger(f"plugin.{self.name}")

        # Validate configuration on initialization
        self.validate_config()

    @property
    @abstractmethod
    def plugin_type(self) -> str:
        """Return the type/category of this plugin."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the version of this plugin."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a description of what this plugin does."""

    @property
    def dependencies(self) -> list[str]:
        """Return list of plugin dependencies (optional)."""
        return []

    @abstractmethod
    def validate_config(self) -> None:
        """Validate the plugin configuration. Raise PluginConfigError if invalid."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the plugin. Called once during plugin loading."""

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources. Called when plugin is unloaded."""

    def is_enabled(self) -> bool:
        """Check if the plugin is enabled."""
        return self.enabled

    def enable(self) -> None:
        """Enable the plugin."""
        self.enabled = True
        self.logger.info(f"Plugin {self.name} enabled")

    def disable(self) -> None:
        """Disable the plugin."""
        self.enabled = False
        self.logger.info(f"Plugin {self.name} disabled")

    def get_info(self) -> dict[str, Any]:
        """Get plugin information."""
        return {
            "name": self.name,
            "type": self.plugin_type,
            "version": self.version,
            "description": self.description,
            "enabled": self.enabled,
            "dependencies": self.dependencies,
            "config": self.config,
        }


class CameraDiscoveryPlugin(BasePlugin):
    """Base class for camera discovery plugins."""

    @property
    def plugin_type(self) -> str:
        return "camera_discovery"

    @abstractmethod
    def discover_cameras(self, **kwargs) -> list[dict[str, Any]]:
        """Discover cameras and return list of camera information.

        Returns:
            List of dictionaries containing camera information
        """

    @abstractmethod
    def test_camera(self, camera_info: dict[str, Any]) -> bool:
        """Test if a discovered camera is accessible.

        Args:
            camera_info: Camera information dictionary

        Returns:
            True if camera is accessible, False otherwise
        """


class AlertPlugin(BasePlugin):
    """Base class for alert/notification plugins."""

    @property
    def plugin_type(self) -> str:
        return "alert"

    @abstractmethod
    def send_alert(self, message: str, **kwargs) -> bool:
        """Send an alert message.

        Args:
            message: The alert message to send
            **kwargs: Additional alert-specific parameters

        Returns:
            True if alert was sent successfully, False otherwise
        """

    @abstractmethod
    def test_connection(self) -> bool:
        """Test the alert mechanism connection.

        Returns:
            True if connection is working, False otherwise
        """


class AIProviderPlugin(BasePlugin):
    """Base class for AI/LLM provider plugins."""

    @property
    def plugin_type(self) -> str:
        return "ai_provider"

    @abstractmethod
    def generate_caption(self, image_data: bytes, **kwargs) -> str:
        """Generate a caption for an image.

        Args:
            image_data: Raw image data
            **kwargs: Additional parameters for caption generation

        Returns:
            Generated caption text
        """

    @abstractmethod
    def ask_question(
        self, question: str, context: str = "", **kwargs
    ) -> tuple[str, bool]:
        """Ask a question to the AI.

        Args:
            question: The question to ask
            context: Optional context for the question
            **kwargs: Additional parameters

        Returns:
            Tuple of (answer, was_truncated)
        """

    @abstractmethod
    def analyze_image(
        self, image_data: bytes, analysis_type: str = "general", **kwargs
    ) -> dict[str, Any]:
        """Analyze an image and return results.

        Args:
            image_data: Raw image data
            analysis_type: Type of analysis to perform
            **kwargs: Additional parameters

        Returns:
            Dictionary containing analysis results
        """


class StoragePlugin(BasePlugin):
    """Base class for storage provider plugins."""

    @property
    def plugin_type(self) -> str:
        return "storage"

    @abstractmethod
    def store_file(self, file_path: str, destination: str, **kwargs) -> str:
        """Store a file in the storage system.

        Args:
            file_path: Local path to the file to store
            destination: Destination path in storage system
            **kwargs: Additional storage parameters

        Returns:
            URL or identifier for the stored file
        """

    @abstractmethod
    def retrieve_file(self, identifier: str, local_path: str, **kwargs) -> bool:
        """Retrieve a file from the storage system.

        Args:
            identifier: File identifier in storage system
            local_path: Local path to save the retrieved file
            **kwargs: Additional parameters

        Returns:
            True if file was retrieved successfully, False otherwise
        """

    @abstractmethod
    def delete_file(self, identifier: str, **kwargs) -> bool:
        """Delete a file from the storage system.

        Args:
            identifier: File identifier in storage system
            **kwargs: Additional parameters

        Returns:
            True if file was deleted successfully, False otherwise
        """

    @abstractmethod
    def list_files(self, prefix: str = "", **kwargs) -> list[dict[str, Any]]:
        """List files in the storage system.

        Args:
            prefix: Optional prefix to filter files
            **kwargs: Additional parameters

        Returns:
            List of file information dictionaries
        """


class ProcessingPlugin(BasePlugin):
    """Base class for data processing plugins."""

    @property
    def plugin_type(self) -> str:
        return "processing"

    @abstractmethod
    def process_data(self, data: Any, **kwargs) -> Any:
        """Process input data and return results.

        Args:
            data: Input data to process
            **kwargs: Additional processing parameters

        Returns:
            Processed data
        """

    @abstractmethod
    def get_supported_formats(self) -> list[str]:
        """Get list of supported data formats.

        Returns:
            List of supported format strings
        """


# Plugin type registry for validation
PLUGIN_TYPES = {
    "camera_discovery": CameraDiscoveryPlugin,
    "alert": AlertPlugin,
    "ai_provider": AIProviderPlugin,
    "storage": StoragePlugin,
    "processing": ProcessingPlugin,
}
