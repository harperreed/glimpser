# ABOUTME: API blueprint for external API endpoints and integrations
# ABOUTME: Handles REST API, webhooks, third-party integrations, and external interfaces

import time
from datetime import datetime

from flask import Blueprint, jsonify, request

from app.config import API_KEY
from app.utils import camera_discovery, template_manager
from app.utils.validators import validate_template_name

api_bp = Blueprint("api", __name__, url_prefix="/api")


def api_key_required(f):
    """Decorator for API endpoints that require API key authentication."""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for API key in headers or query params
        api_key = (
            request.headers.get("X-API-Key")
            or request.headers.get("Authorization", "").replace("Bearer ", "")
            or request.args.get("api_key")
        )

        if api_key != API_KEY:
            return jsonify({"error": "Invalid or missing API key"}), 401

        return f(*args, **kwargs)

    return decorated_function


@api_bp.route("/discover", methods=["GET"])
@api_key_required
def api_discover():
    """API endpoint for camera discovery."""
    try:
        # Get discovery parameters
        cidr = request.args.get("cidr")
        timeout = request.args.get("timeout", 30, type=int)

        # Perform camera discovery
        discovered_cameras = camera_discovery.discover_cameras(cidr, timeout)

        return jsonify(
            {
                "success": True,
                "cameras": discovered_cameras,
                "count": len(discovered_cameras),
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/cameras", methods=["GET"])
@api_key_required
def list_cameras():
    """List all configured cameras."""
    try:
        templates = template_manager.get_templates()

        cameras = []
        for name, details in templates.items():
            cameras.append(
                {
                    "name": name,
                    "url": details.get("url"),
                    "group": details.get("group"),
                    "status": details.get("status", "unknown"),
                    "last_seen": details.get("last_seen"),
                }
            )

        return jsonify({"success": True, "cameras": cameras, "count": len(cameras)})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/cameras/<string:camera_name>", methods=["GET"])
@api_key_required
def get_camera(camera_name):
    """Get details for a specific camera."""
    camera_name = validate_template_name(camera_name)
    if not camera_name:
        return jsonify({"error": "Invalid camera name"}), 400

    try:
        details = template_manager.get_template(camera_name)

        if not details:
            return jsonify({"error": "Camera not found"}), 404

        return jsonify({"success": True, "camera": {"name": camera_name, **details}})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/cameras/<string:camera_name>", methods=["PUT", "POST"])
@api_key_required
def update_camera(camera_name):
    """Update camera configuration."""
    camera_name = validate_template_name(camera_name)
    if not camera_name:
        return jsonify({"error": "Invalid camera name"}), 400

    if not request.is_json:
        return jsonify({"error": "JSON payload required"}), 400

    try:
        # Update camera configuration
        config = request.json
        success = template_manager.update_template(camera_name, config)

        if success:
            return jsonify(
                {
                    "success": True,
                    "message": f"Camera {camera_name} updated successfully",
                }
            )
        else:
            return jsonify({"success": False, "error": "Failed to update camera"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/cameras/<string:camera_name>", methods=["DELETE"])
@api_key_required
def delete_camera(camera_name):
    """Delete a camera configuration."""
    camera_name = validate_template_name(camera_name)
    if not camera_name:
        return jsonify({"error": "Invalid camera name"}), 400

    try:
        success = template_manager.delete_template(camera_name)

        if success:
            return jsonify(
                {
                    "success": True,
                    "message": f"Camera {camera_name} deleted successfully",
                }
            )
        else:
            return jsonify({"success": False, "error": "Failed to delete camera"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/capture/<string:camera_name>", methods=["POST"])
@api_key_required
def api_capture(camera_name):
    """API endpoint to capture screenshot from camera."""
    camera_name = validate_template_name(camera_name)
    if not camera_name:
        return jsonify({"error": "Invalid camera name"}), 400

    try:
        from app.utils import screenshots

        screenshot_path = screenshots.capture_screenshot(camera_name)

        if screenshot_path:
            return jsonify(
                {
                    "success": True,
                    "camera": camera_name,
                    "screenshot_path": screenshot_path,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        else:
            return jsonify(
                {"success": False, "error": "Failed to capture screenshot"}
            ), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/status", methods=["GET"])
@api_key_required
def api_status():
    """Get API status and system information."""
    try:
        from app.config import VERSION

        status = {
            "api_version": "v1",
            "application_version": str(VERSION),
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "endpoints": {
                "discover": "/api/discover",
                "cameras": "/api/cameras",
                "capture": "/api/capture/<camera_name>",
                "webhooks": "/api/webhooks",
                "events": "/api/events",
            },
        }

        return jsonify(status)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/webhooks", methods=["POST"])
@api_key_required
def webhook_handler():
    """Handle incoming webhooks."""
    if not request.is_json:
        return jsonify({"error": "JSON payload required"}), 400

    try:
        webhook_data = request.json
        event_type = webhook_data.get("event_type")

        # Process webhook based on event type
        if event_type == "camera_alert":
            result = process_camera_alert(webhook_data)
        elif event_type == "motion_detected":
            result = process_motion_detection(webhook_data)
        elif event_type == "system_event":
            result = process_system_event(webhook_data)
        else:
            return jsonify({"error": f"Unknown event type: {event_type}"}), 400

        return jsonify(
            {
                "success": True,
                "event_type": event_type,
                "result": result,
                "processed_at": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/events", methods=["GET"])
@api_key_required
def list_events():
    """List recent system events."""
    try:
        limit = request.args.get("limit", 100, type=int)
        event_type = request.args.get("type")

        events = get_recent_events(limit, event_type)

        return jsonify({"success": True, "events": events, "count": len(events)})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/events", methods=["POST"])
@api_key_required
def create_event():
    """Create a new system event."""
    if not request.is_json:
        return jsonify({"error": "JSON payload required"}), 400

    try:
        event_data = request.json
        event_id = create_system_event(event_data)

        return jsonify(
            {
                "success": True,
                "event_id": event_id,
                "message": "Event created successfully",
            }
        ), 201

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/stream/<string:camera_name>", methods=["GET"])
@api_key_required
def api_stream_url(camera_name):
    """Get streaming URL for a camera."""
    camera_name = validate_template_name(camera_name)
    if not camera_name:
        return jsonify({"error": "Invalid camera name"}), 400

    try:
        details = template_manager.get_template(camera_name)

        if not details:
            return jsonify({"error": "Camera not found"}), 404

        # Generate streaming URLs
        base_url = request.host_url.rstrip("/")

        stream_urls = {
            "mjpg": f"{base_url}/stream.mjpg?camera={camera_name}",
            "mp4": f"{base_url}/stream.mp4?camera={camera_name}",
            "hls": f"{base_url}/stream.m3u8?camera={camera_name}",
            "snapshot": f"{base_url}/capture/{camera_name}",
        }

        return jsonify(
            {"success": True, "camera": camera_name, "stream_urls": stream_urls}
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/health", methods=["GET"])
def api_health():
    """Public API health check (no auth required)."""
    return jsonify(
        {
            "status": "healthy",
            "api_version": "v1",
            "timestamp": datetime.now().isoformat(),
        }
    )


@api_bp.errorhandler(404)
def api_not_found(error):
    """Custom 404 handler for API routes."""
    return jsonify({"error": "API endpoint not found", "status_code": 404}), 404


@api_bp.errorhandler(500)
def api_internal_error(error):
    """Custom 500 handler for API routes."""
    return jsonify({"error": "Internal server error", "status_code": 500}), 500


# Helper functions
def process_camera_alert(webhook_data):
    """Process camera alert webhook."""
    camera_name = webhook_data.get("camera_name")
    alert_type = webhook_data.get("alert_type")

    # Process the alert
    return {"processed": True, "camera": camera_name, "alert_type": alert_type}


def process_motion_detection(webhook_data):
    """Process motion detection webhook."""
    camera_name = webhook_data.get("camera_name")
    confidence = webhook_data.get("confidence", 0.0)

    # Process motion detection
    return {"processed": True, "camera": camera_name, "confidence": confidence}


def process_system_event(webhook_data):
    """Process system event webhook."""
    event_name = webhook_data.get("event_name")
    severity = webhook_data.get("severity", "info")

    # Process system event
    return {"processed": True, "event": event_name, "severity": severity}


def get_recent_events(limit, event_type):
    """Get recent system events."""
    # Placeholder implementation
    events = []
    for i in range(min(limit, 10)):
        events.append(
            {
                "id": f"event_{i}",
                "type": event_type or "system",
                "timestamp": datetime.now().isoformat(),
                "message": f"Sample event {i}",
            }
        )

    return events


def create_system_event(event_data):
    """Create a new system event."""
    # Placeholder implementation
    event_id = f"event_{int(time.time())}"

    # Store the event
    return event_id
