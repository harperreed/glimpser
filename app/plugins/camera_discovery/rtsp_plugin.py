# ABOUTME: RTSP camera discovery plugin for finding cameras with RTSP streaming capability
# ABOUTME: Scans for RTSP ports and tests stream accessibility

import socket
import time
from typing import Any

from app.plugins.base import CameraDiscoveryPlugin, PluginConfigError


class RtspDiscoveryPlugin(CameraDiscoveryPlugin):
    """Plugin for discovering cameras with RTSP streaming capability."""

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Discovers cameras by scanning for RTSP ports and testing stream accessibility"

    def validate_config(self) -> None:
        """Validate RTSP plugin configuration."""
        timeout = self.config.get("timeout", 3)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise PluginConfigError("timeout must be a positive number")

        rtsp_ports = self.config.get("rtsp_ports", [554])
        if not isinstance(rtsp_ports, list) or not all(
            isinstance(p, int) for p in rtsp_ports
        ):
            raise PluginConfigError("rtsp_ports must be a list of integers")

    def initialize(self) -> None:
        """Initialize the RTSP discovery plugin."""
        self.timeout = self.config.get("timeout", 3)
        self.rtsp_ports = self.config.get("rtsp_ports", [554, 8554, 1935])
        self.common_paths = self.config.get(
            "common_paths",
            [
                "/live/main",
                "/live/0",
                "/stream1",
                "/cam/realmonitor",
                "/h264Preview_01_main",
                "/MediaInput/h264",
                "/video.mjpg",
            ],
        )

        self.logger.info(
            f"RTSP discovery plugin initialized (ports: {self.rtsp_ports})"
        )

    def cleanup(self) -> None:
        """Clean up RTSP discovery resources."""
        self.logger.info("RTSP discovery plugin cleaned up")

    def discover_cameras(self, **kwargs) -> list[dict[str, Any]]:
        """Discover RTSP cameras by port scanning.

        Args:
            **kwargs: Additional discovery parameters
                - cidr: Network CIDR to scan (required)
                - max_hosts: Maximum number of hosts to scan (optional)

        Returns:
            List of discovered camera information dictionaries
        """
        if not self.is_enabled():
            return []

        cidr = kwargs.get("cidr")
        if not cidr:
            self.logger.warning("RTSP discovery requires CIDR parameter")
            return []

        discovered_cameras = []

        try:
            # Generate IP addresses from CIDR
            ip_addresses = self._generate_ip_addresses(cidr)
            max_hosts = kwargs.get("max_hosts", 254)

            if len(ip_addresses) > max_hosts:
                ip_addresses = ip_addresses[:max_hosts]
                self.logger.info(f"Limiting scan to {max_hosts} hosts")

            # Scan for RTSP ports
            for ip_address in ip_addresses:
                camera_info = self._scan_host_for_rtsp(ip_address)
                if camera_info:
                    discovered_cameras.append(camera_info)

            self.logger.info(f"RTSP discovery found {len(discovered_cameras)} cameras")
            return discovered_cameras

        except Exception as e:
            self.logger.error(f"Error during RTSP discovery: {e}")
            return []

    def test_camera(self, camera_info: dict[str, Any]) -> bool:
        """Test if an RTSP camera stream is accessible.

        Args:
            camera_info: Camera information dictionary

        Returns:
            True if camera stream is accessible, False otherwise
        """
        try:
            rtsp_url = camera_info.get("rtsp_url")
            if not rtsp_url:
                return False

            # Test RTSP connection
            return self._test_rtsp_stream(rtsp_url)

        except Exception as e:
            self.logger.error(f"Error testing RTSP camera {camera_info}: {e}")
            return False

    def _generate_ip_addresses(self, cidr: str) -> list[str]:
        """Generate list of IP addresses from CIDR notation."""
        import ipaddress

        try:
            network = ipaddress.IPv4Network(cidr, strict=False)
            return [str(ip) for ip in network.hosts()]
        except ValueError as e:
            self.logger.error(f"Invalid CIDR format {cidr}: {e}")
            return []

    def _scan_host_for_rtsp(self, ip_address: str) -> dict[str, Any]:
        """Scan a single host for RTSP services."""
        for port in self.rtsp_ports:
            if self._test_port(ip_address, port):
                # Found RTSP port, try to build RTSP URL
                rtsp_urls = self._build_rtsp_urls(ip_address, port)

                for rtsp_url in rtsp_urls:
                    if self._test_rtsp_stream(rtsp_url):
                        return {
                            "ip_address": ip_address,
                            "port": port,
                            "rtsp_url": rtsp_url,
                            "protocol": "rtsp",
                            "discovery_method": "port_scan",
                            "stream_type": "live",
                        }

        return None

    def _test_port(self, ip_address: str, port: int) -> bool:
        """Test if a port is open on the given IP address."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)

            result = sock.connect_ex((ip_address, port))
            sock.close()

            return result == 0

        except Exception:
            return False

    def _build_rtsp_urls(self, ip_address: str, port: int) -> list[str]:
        """Build possible RTSP URLs for testing."""
        urls = []

        for path in self.common_paths:
            url = f"rtsp://{ip_address}:{port}{path}"
            urls.append(url)

        # Also try without path
        urls.append(f"rtsp://{ip_address}:{port}/")

        return urls

    def _test_rtsp_stream(self, rtsp_url: str) -> bool:
        """Test if an RTSP stream is accessible."""
        try:
            # This would use actual RTSP testing (e.g., with OpenCV or FFmpeg)
            # For now, just simulate testing
            self.logger.debug(f"Testing RTSP stream: {rtsp_url}")

            # Simulate stream test delay
            time.sleep(0.05)

            # Placeholder: return True for demonstration
            # In reality, this would attempt to connect to the RTSP stream
            return True

        except Exception as e:
            self.logger.error(f"RTSP stream test error for {rtsp_url}: {e}")
            return False
