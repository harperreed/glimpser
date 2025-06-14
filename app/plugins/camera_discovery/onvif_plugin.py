# ABOUTME: ONVIF camera discovery plugin for finding IP cameras using ONVIF protocol
# ABOUTME: Scans networks for ONVIF-compatible devices and retrieves camera information

import socket
import time
from typing import Any

from app.plugins.base import CameraDiscoveryPlugin, PluginConfigError


class OnvifDiscoveryPlugin(CameraDiscoveryPlugin):
    """Plugin for discovering cameras using ONVIF protocol."""

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Discovers IP cameras using ONVIF protocol via multicast and direct scanning"

    @property
    def dependencies(self) -> list[str]:
        return ["onvif-zeep"]  # Would require onvif-zeep package

    def validate_config(self) -> None:
        """Validate ONVIF plugin configuration."""
        # Check required configuration
        timeout = self.config.get("timeout", 5)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise PluginConfigError("timeout must be a positive number")

        port_range = self.config.get("port_range", [80, 8080])
        if not isinstance(port_range, list) or len(port_range) != 2:
            raise PluginConfigError("port_range must be a list of two integers")

    def initialize(self) -> None:
        """Initialize the ONVIF discovery plugin."""
        self.timeout = self.config.get("timeout", 5)
        self.port_range = self.config.get("port_range", [80, 8080])
        self.multicast_address = self.config.get("multicast_address", "239.255.255.250")
        self.multicast_port = self.config.get("multicast_port", 3702)

        self.logger.info(
            f"ONVIF discovery plugin initialized (timeout: {self.timeout}s)"
        )

    def cleanup(self) -> None:
        """Clean up ONVIF discovery resources."""
        self.logger.info("ONVIF discovery plugin cleaned up")

    def discover_cameras(self, **kwargs) -> list[dict[str, Any]]:
        """Discover ONVIF cameras on the network.

        Args:
            **kwargs: Additional discovery parameters
                - cidr: Network CIDR to scan (optional)
                - use_multicast: Whether to use multicast discovery (default: True)

        Returns:
            List of discovered camera information dictionaries
        """
        if not self.is_enabled():
            return []

        discovered_cameras = []

        try:
            # Use multicast discovery if enabled
            if kwargs.get("use_multicast", True):
                multicast_cameras = self._discover_via_multicast()
                discovered_cameras.extend(multicast_cameras)
                self.logger.info(
                    f"Found {len(multicast_cameras)} cameras via multicast"
                )

            # Direct network scanning if CIDR provided
            cidr = kwargs.get("cidr")
            if cidr:
                scanned_cameras = self._discover_via_scan(cidr)
                discovered_cameras.extend(scanned_cameras)
                self.logger.info(
                    f"Found {len(scanned_cameras)} cameras via network scan"
                )

            # Remove duplicates based on IP address
            unique_cameras = self._deduplicate_cameras(discovered_cameras)

            self.logger.info(
                f"Total unique ONVIF cameras discovered: {len(unique_cameras)}"
            )
            return unique_cameras

        except Exception as e:
            self.logger.error(f"Error during ONVIF discovery: {e}")
            return []

    def test_camera(self, camera_info: dict[str, Any]) -> bool:
        """Test if an ONVIF camera is accessible.

        Args:
            camera_info: Camera information dictionary

        Returns:
            True if camera is accessible, False otherwise
        """
        try:
            ip_address = camera_info.get("ip_address")
            port = camera_info.get("port", 80)

            if not ip_address:
                return False

            # Test basic connectivity
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)

            result = sock.connect_ex((ip_address, int(port)))
            sock.close()

            if result == 0:
                # Further ONVIF-specific testing could be done here
                return self._test_onvif_service(ip_address, port)

            return False

        except Exception as e:
            self.logger.error(f"Error testing ONVIF camera {camera_info}: {e}")
            return False

    def _discover_via_multicast(self) -> list[dict[str, Any]]:
        """Discover cameras using ONVIF multicast."""
        cameras = []

        try:
            # This would implement actual ONVIF multicast discovery
            # For now, returning placeholder data
            self.logger.debug("Performing ONVIF multicast discovery")

            # Simulate multicast discovery
            time.sleep(0.1)  # Simulate network delay

            # Placeholder discovered cameras
            cameras.append(
                {
                    "ip_address": "192.168.1.100",
                    "port": 80,
                    "manufacturer": "Hikvision",
                    "model": "DS-2CD2043G0-I",
                    "onvif_url": "http://192.168.1.100/onvif/device_service",
                    "discovery_method": "multicast",
                    "protocol": "onvif",
                }
            )

        except Exception as e:
            self.logger.error(f"Multicast discovery error: {e}")

        return cameras

    def _discover_via_scan(self, cidr: str) -> list[dict[str, Any]]:
        """Discover cameras by scanning network range."""
        cameras = []

        try:
            self.logger.debug(f"Scanning network {cidr} for ONVIF cameras")

            # This would implement actual network scanning
            # For now, returning placeholder data
            time.sleep(0.2)  # Simulate scanning delay

            # Placeholder scanned cameras
            cameras.append(
                {
                    "ip_address": "192.168.1.101",
                    "port": 8080,
                    "manufacturer": "Dahua",
                    "model": "IPC-HFW4431R-Z",
                    "onvif_url": "http://192.168.1.101:8080/onvif/device_service",
                    "discovery_method": "scan",
                    "protocol": "onvif",
                }
            )

        except Exception as e:
            self.logger.error(f"Network scan error: {e}")

        return cameras

    def _test_onvif_service(self, ip_address: str, port: int) -> bool:
        """Test ONVIF service availability."""
        try:
            # This would test actual ONVIF service
            # For now, just return True if connection was successful
            self.logger.debug(f"Testing ONVIF service at {ip_address}:{port}")
            return True

        except Exception as e:
            self.logger.error(f"ONVIF service test error: {e}")
            return False

    def _deduplicate_cameras(
        self, cameras: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Remove duplicate cameras based on IP address."""
        seen_ips = set()
        unique_cameras = []

        for camera in cameras:
            ip = camera.get("ip_address")
            if ip and ip not in seen_ips:
                seen_ips.add(ip)
                unique_cameras.append(camera)

        return unique_cameras
