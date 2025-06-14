# ABOUTME: Capture blueprint for screenshot and video capture endpoints
# ABOUTME: Handles frame capture, video recording, and screenshot generation

import os

from flask import Blueprint, Response, abort, jsonify, request, send_file

from app.blueprints.auth import login_required
from app.config import SCREENSHOT_DIRECTORY, VIDEO_DIRECTORY
from app.utils import screenshots, video_archiver
from app.utils.validators import validate_template_name

capture_bp = Blueprint("capture", __name__)


@capture_bp.route("/capture/<string:template_name>", methods=["POST"])
@login_required
def capture_screenshot(template_name):
    """Capture a screenshot from the specified camera template."""
    template_name = validate_template_name(template_name)
    if not template_name:
        abort(400, "Invalid template name")

    try:
        # Capture screenshot using the screenshots utility
        screenshot_path = screenshots.capture_screenshot(template_name)

        if screenshot_path and os.path.exists(screenshot_path):
            return jsonify(
                {
                    "success": True,
                    "path": screenshot_path,
                    "message": f"Screenshot captured for {template_name}",
                }
            )
        else:
            return jsonify(
                {
                    "success": False,
                    "message": f"Failed to capture screenshot for {template_name}",
                }
            ), 500

    except Exception as e:
        return jsonify(
            {"success": False, "message": f"Error capturing screenshot: {str(e)}"}
        ), 500


@capture_bp.route("/capture/frame/<string:template_name>", methods=["POST"])
@login_required
def capture_frame(template_name):
    """Capture a single frame from the camera stream."""
    template_name = validate_template_name(template_name)
    if not template_name:
        abort(400, "Invalid template name")

    try:
        # Capture frame from stream
        frame_data = screenshots.capture_frame_from_stream(template_name)

        if frame_data:
            return Response(frame_data, mimetype="image/jpeg")
        else:
            abort(404, "Could not capture frame")

    except Exception as e:
        return jsonify(
            {"success": False, "message": f"Error capturing frame: {str(e)}"}
        ), 500


@capture_bp.route("/record/start/<string:template_name>", methods=["POST"])
@login_required
def start_recording(template_name):
    """Start video recording for the specified camera."""
    template_name = validate_template_name(template_name)
    if not template_name:
        abort(400, "Invalid template name")

    duration = request.json.get("duration", 30) if request.is_json else 30

    try:
        # Start video recording
        recording_id = video_archiver.start_recording(template_name, duration)

        return jsonify(
            {
                "success": True,
                "recording_id": recording_id,
                "message": f"Started recording for {template_name}",
            }
        )

    except Exception as e:
        return jsonify(
            {"success": False, "message": f"Error starting recording: {str(e)}"}
        ), 500


@capture_bp.route("/record/stop/<string:recording_id>", methods=["POST"])
@login_required
def stop_recording(recording_id):
    """Stop an active video recording."""
    try:
        # Stop video recording
        video_path = video_archiver.stop_recording(recording_id)

        if video_path:
            return jsonify(
                {
                    "success": True,
                    "video_path": video_path,
                    "message": "Recording stopped successfully",
                }
            )
        else:
            return jsonify(
                {"success": False, "message": "Recording not found or already stopped"}
            ), 404

    except Exception as e:
        return jsonify(
            {"success": False, "message": f"Error stopping recording: {str(e)}"}
        ), 500


@capture_bp.route("/record/status/<string:recording_id>", methods=["GET"])
@login_required
def recording_status(recording_id):
    """Get the status of a video recording."""
    try:
        status = video_archiver.get_recording_status(recording_id)

        if status:
            return jsonify({"success": True, "status": status})
        else:
            return jsonify({"success": False, "message": "Recording not found"}), 404

    except Exception as e:
        return jsonify(
            {"success": False, "message": f"Error getting recording status: {str(e)}"}
        ), 500


@capture_bp.route("/screenshots/<string:template_name>", methods=["GET"])
@login_required
def list_screenshots(template_name):
    """List available screenshots for a camera template."""
    template_name = validate_template_name(template_name)
    if not template_name:
        abort(400, "Invalid template name")

    try:
        screenshot_dir = os.path.join(SCREENSHOT_DIRECTORY, template_name)

        if not os.path.exists(screenshot_dir):
            return jsonify({"screenshots": []})

        screenshots_list = []
        for filename in os.listdir(screenshot_dir):
            if filename.lower().endswith((".jpg", ".jpeg", ".png")):
                file_path = os.path.join(screenshot_dir, filename)
                stat = os.stat(file_path)
                screenshots_list.append(
                    {
                        "filename": filename,
                        "path": file_path,
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                    }
                )

        # Sort by modification time (newest first)
        screenshots_list.sort(key=lambda x: x["modified"], reverse=True)

        return jsonify({"screenshots": screenshots_list})

    except Exception as e:
        return jsonify(
            {"success": False, "message": f"Error listing screenshots: {str(e)}"}
        ), 500


@capture_bp.route(
    "/screenshot/<string:template_name>/<string:filename>", methods=["GET"]
)
@login_required
def serve_screenshot(template_name, filename):
    """Serve a specific screenshot file."""
    template_name = validate_template_name(template_name)
    if not template_name:
        abort(400, "Invalid template name")

    # Validate filename to prevent directory traversal
    if ".." in filename or "/" in filename:
        abort(400, "Invalid filename")

    screenshot_path = os.path.join(SCREENSHOT_DIRECTORY, template_name, filename)

    if not os.path.exists(screenshot_path):
        abort(404, "Screenshot not found")

    return send_file(screenshot_path)


@capture_bp.route("/videos/<string:template_name>", methods=["GET"])
@login_required
def list_videos(template_name):
    """List available videos for a camera template."""
    template_name = validate_template_name(template_name)
    if not template_name:
        abort(400, "Invalid template name")

    try:
        video_dir = os.path.join(VIDEO_DIRECTORY, template_name)

        if not os.path.exists(video_dir):
            return jsonify({"videos": []})

        videos_list = []
        for filename in os.listdir(video_dir):
            if filename.lower().endswith((".mp4", ".avi", ".mov")):
                file_path = os.path.join(video_dir, filename)
                stat = os.stat(file_path)
                videos_list.append(
                    {
                        "filename": filename,
                        "path": file_path,
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                    }
                )

        # Sort by modification time (newest first)
        videos_list.sort(key=lambda x: x["modified"], reverse=True)

        return jsonify({"videos": videos_list})

    except Exception as e:
        return jsonify(
            {"success": False, "message": f"Error listing videos: {str(e)}"}
        ), 500


@capture_bp.route("/video/<string:template_name>/<string:filename>", methods=["GET"])
@login_required
def serve_video(template_name, filename):
    """Serve a specific video file."""
    template_name = validate_template_name(template_name)
    if not template_name:
        abort(400, "Invalid template name")

    # Validate filename to prevent directory traversal
    if ".." in filename or "/" in filename:
        abort(400, "Invalid filename")

    video_path = os.path.join(VIDEO_DIRECTORY, template_name, filename)

    if not os.path.exists(video_path):
        abort(404, "Video not found")

    return send_file(video_path)


@capture_bp.route("/capture/bulk", methods=["POST"])
@login_required
def bulk_capture():
    """Capture screenshots from multiple cameras simultaneously."""
    if not request.is_json:
        abort(400, "JSON payload required")

    templates = request.json.get("templates", [])
    if not templates:
        abort(400, "Templates list required")

    results = []

    for template_name in templates:
        template_name = validate_template_name(template_name)
        if not template_name:
            results.append(
                {
                    "template": template_name,
                    "success": False,
                    "message": "Invalid template name",
                }
            )
            continue

        try:
            screenshot_path = screenshots.capture_screenshot(template_name)

            if screenshot_path and os.path.exists(screenshot_path):
                results.append(
                    {
                        "template": template_name,
                        "success": True,
                        "path": screenshot_path,
                    }
                )
            else:
                results.append(
                    {
                        "template": template_name,
                        "success": False,
                        "message": "Failed to capture screenshot",
                    }
                )

        except Exception as e:
            results.append(
                {"template": template_name, "success": False, "message": str(e)}
            )

    return jsonify({"results": results})
