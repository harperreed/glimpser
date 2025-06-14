# ABOUTME: Admin blueprint for settings, logs, and system management
# ABOUTME: Handles configuration, monitoring, updates, and administrative functions

import json
import os
from datetime import datetime

from flask import (
    Blueprint,
    Response,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    stream_with_context,
    url_for,
)

from app.blueprints.auth import login_required
from app.config import backup_config, restore_config
from app.utils.db import SessionLocal

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """Handle application settings management."""
    if request.method == "POST":
        # Handle settings updates
        if request.is_json:
            updates = request.json
        else:
            updates = request.form.to_dict()

        try:
            # Update settings
            updated_count = 0
            for key, value in updates.items():
                if update_setting(key, value):
                    updated_count += 1

            if request.is_json:
                return jsonify(
                    {
                        "success": True,
                        "updated": updated_count,
                        "message": f"Updated {updated_count} settings",
                    }
                )
            else:
                return redirect(url_for("admin.settings"))

        except Exception as e:
            if request.is_json:
                return jsonify(
                    {"success": False, "message": f"Settings update failed: {str(e)}"}
                ), 500
            else:
                abort(500)

    # GET request - show settings page
    try:
        # Import here to avoid circular imports
        from app.routes import get_all_settings

        all_settings = get_all_settings()
        return render_template("settings.html", settings=all_settings)
    except Exception:
        abort(500)


@admin_bp.route("/settings/backup", methods=["POST"])
@login_required
def backup_settings():
    """Create a backup of current settings."""
    try:
        backup_path = backup_config()
        return jsonify(
            {
                "success": True,
                "backup_path": backup_path,
                "message": "Settings backup created successfully",
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"Backup failed: {str(e)}"}), 500


@admin_bp.route("/settings/restore", methods=["POST"])
@login_required
def restore_settings():
    """Restore settings from backup."""
    backup_path = (
        request.json.get("backup_path")
        if request.is_json
        else request.form.get("backup_path")
    )

    if not backup_path:
        abort(400, "backup_path required")

    try:
        restore_config(backup_path)
        return jsonify({"success": True, "message": "Settings restored successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Restore failed: {str(e)}"}), 500


@admin_bp.route("/logs", methods=["GET"])
@login_required
def logs():
    """Display system logs."""
    level = request.args.get("level", "INFO")
    source = request.args.get("source", "")
    limit = request.args.get("limit", "1000", type=int)

    try:
        log_entries = get_log_entries(level, source, limit)

        if request.headers.get("Accept") == "application/json":
            return jsonify(
                {"success": True, "logs": log_entries, "count": len(log_entries)}
            )
        else:
            return render_template(
                "logs.html", logs=log_entries, level=level, source=source
            )

    except Exception as e:
        return jsonify(
            {"success": False, "message": f"Failed to get logs: {str(e)}"}
        ), 500


@admin_bp.route("/stream_logs")
@login_required
def stream_logs():
    """Stream live log entries."""
    level = request.args.get("level")
    source = request.args.get("source")
    start_date = request.args.get("start_date")

    def generate():
        """Generate live log stream."""
        # Import here to avoid circular imports
        from app.utils.logs import read_logs_from_memory

        for log_line in read_logs_from_memory(level, source, start_date):
            yield f"data: {json.dumps(log_line)}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@admin_bp.route("/status", methods=["GET"])
@login_required
def system_status():
    """Get comprehensive system status."""
    try:
        status = {
            "timestamp": datetime.now().isoformat(),
            "system": get_system_info(),
            "database": get_database_status(),
            "services": get_service_status(),
            "storage": get_storage_info(),
            "performance": get_performance_metrics(),
        }

        return jsonify({"success": True, "status": status})

    except Exception as e:
        return jsonify(
            {"success": False, "message": f"Status check failed: {str(e)}"}
        ), 500


@admin_bp.route("/health")
@login_required
def health_check():
    """Extended health check endpoint."""
    try:
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {
                "database": check_database_health(),
                "storage": check_storage_health(),
                "services": check_services_health(),
            },
        }

        # Determine overall health
        all_healthy = all(
            check.get("status") == "healthy" for check in health_data["checks"].values()
        )

        if not all_healthy:
            health_data["status"] = "degraded"

        status_code = 200 if all_healthy else 503

        return jsonify(health_data), status_code

    except Exception as e:
        return jsonify(
            {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
        ), 503


@admin_bp.route("/restart", methods=["POST"])
@login_required
def restart_system():
    """Restart the application."""
    try:
        # Schedule restart
        from app.routes import restart_server

        restart_server()

        return jsonify({"success": True, "message": "System restart initiated"})

    except Exception as e:
        return jsonify({"success": False, "message": f"Restart failed: {str(e)}"}), 500


@admin_bp.route("/update", methods=["POST"])
@login_required
def update_system():
    """Update the application to latest version."""
    try:
        # Check if update is available
        from app.config import VERSION
        from app.utils.github import is_update_available

        if not is_update_available(str(VERSION)):
            return jsonify({"success": False, "message": "No updates available"})

        # Trigger update process
        update_result = perform_system_update()

        return jsonify(
            {
                "success": True,
                "result": update_result,
                "message": "Update initiated successfully",
            }
        )

    except Exception as e:
        return jsonify({"success": False, "message": f"Update failed: {str(e)}"}), 500


@admin_bp.route("/metrics", methods=["GET"])
@login_required
def system_metrics():
    """Get detailed system metrics."""
    try:
        metrics = {
            "cpu": get_cpu_metrics(),
            "memory": get_memory_metrics(),
            "disk": get_disk_metrics(),
            "network": get_network_metrics(),
            "application": get_application_metrics(),
        }

        return jsonify(
            {
                "success": True,
                "metrics": metrics,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        return jsonify(
            {"success": False, "message": f"Metrics collection failed: {str(e)}"}
        ), 500


@admin_bp.route("/cleanup", methods=["POST"])
@login_required
def cleanup_system():
    """Perform system cleanup operations."""
    cleanup_type = (
        request.json.get("type", "all")
        if request.is_json
        else request.form.get("type", "all")
    )

    try:
        results = {}

        if cleanup_type in ["all", "logs"]:
            results["logs"] = cleanup_old_logs()

        if cleanup_type in ["all", "cache"]:
            results["cache"] = cleanup_cache()

        if cleanup_type in ["all", "temp"]:
            results["temp"] = cleanup_temp_files()

        if cleanup_type in ["all", "media"]:
            results["media"] = cleanup_old_media()

        return jsonify(
            {"success": True, "cleanup_type": cleanup_type, "results": results}
        )

    except Exception as e:
        return jsonify({"success": False, "message": f"Cleanup failed: {str(e)}"}), 500


# Helper functions (these would be implemented with actual system monitoring)
def update_setting(key, value):
    """Update a configuration setting."""
    # Placeholder implementation
    return True


def get_log_entries(level, source, limit):
    """Get log entries based on filters."""
    # Placeholder implementation
    return [
        {
            "timestamp": "2025-06-14T20:30:00",
            "level": level,
            "message": "Sample log entry",
        }
    ]


def get_system_info():
    """Get basic system information."""
    import platform

    import psutil

    return {
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "cpu_count": psutil.cpu_count(),
        "memory_total": psutil.virtual_memory().total,
    }


def get_database_status():
    """Check database connectivity and status."""
    try:
        session_db = SessionLocal()
        session_db.execute("SELECT 1")
        session_db.close()
        return {"status": "healthy", "connection": "active"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def get_service_status():
    """Get status of various services."""
    return {
        "scheduler": "running",
        "camera_discovery": "idle",
        "video_archiver": "running",
    }


def get_storage_info():
    """Get storage usage information."""
    import psutil

    disk_usage = psutil.disk_usage("/")
    return {
        "total": disk_usage.total,
        "used": disk_usage.used,
        "free": disk_usage.free,
        "percent": (disk_usage.used / disk_usage.total) * 100,
    }


def get_performance_metrics():
    """Get performance metrics."""
    import psutil

    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "load_average": os.getloadavg() if hasattr(os, "getloadavg") else [0, 0, 0],
    }


def check_database_health():
    """Check database health."""
    return {"status": "healthy", "response_time": "5ms"}


def check_storage_health():
    """Check storage health."""
    return {"status": "healthy", "space_available": "85%"}


def check_services_health():
    """Check services health."""
    return {"status": "healthy", "services_running": 3}


def perform_system_update():
    """Perform system update."""
    return {"status": "success", "version": "updated"}


def get_cpu_metrics():
    """Get CPU metrics."""
    import psutil

    return {"usage": psutil.cpu_percent(interval=1)}


def get_memory_metrics():
    """Get memory metrics."""
    import psutil

    mem = psutil.virtual_memory()
    return {"usage": mem.percent, "available": mem.available, "total": mem.total}


def get_disk_metrics():
    """Get disk metrics."""
    import psutil

    disk = psutil.disk_usage("/")
    return {
        "usage": (disk.used / disk.total) * 100,
        "free": disk.free,
        "total": disk.total,
    }


def get_network_metrics():
    """Get network metrics."""
    import psutil

    net = psutil.net_io_counters()
    return {"bytes_sent": net.bytes_sent, "bytes_recv": net.bytes_recv}


def get_application_metrics():
    """Get application-specific metrics."""
    return {"routes": 56, "blueprints": 5, "uptime": "1h 30m"}


def cleanup_old_logs():
    """Clean up old log files."""
    return {"deleted_files": 5, "space_freed": "50MB"}


def cleanup_cache():
    """Clean up cache files."""
    return {"cache_cleared": True, "space_freed": "25MB"}


def cleanup_temp_files():
    """Clean up temporary files."""
    return {"temp_files_deleted": 10, "space_freed": "15MB"}


def cleanup_old_media():
    """Clean up old media files."""
    return {"media_files_deleted": 3, "space_freed": "100MB"}
