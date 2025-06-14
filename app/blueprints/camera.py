# ABOUTME: Camera blueprint for camera discovery, configuration, and streaming routes
# ABOUTME: Handles RTSP streams, MJPG endpoints, camera discovery, and live streaming

import os
from collections.abc import Generator

from flask import (
    Blueprint,
    Response,
    abort,
    render_template,
    request,
    stream_with_context,
)

from app.blueprints.auth import login_required
from app.config import VIDEO_DIRECTORY
from app.utils import template_manager
from app.utils.validators import validate_template_name

camera_bp = Blueprint("camera", __name__)


def generate_live_stream(url: str) -> Generator[bytes, None, None]:
    """Generate a live video stream from a camera URL.

    Some camera APIs expose JPEG snapshots rather than a continuous video
    stream. If the URL resembles a static image endpoint, poll the image
    repeatedly to create a pseudo-stream. Otherwise, expect a continuous
    MP4 stream whenever possible.
    """
    import logging
    import time

    import requests

    session = requests.Session()

    # Check if this looks like a snapshot URL
    if url.endswith((".jpg", ".jpeg", ".png")) or "snapshot" in url.lower():
        # Snapshot polling mode
        while True:
            try:
                resp = session.get(url, timeout=5, stream=True)
                if resp.status_code == 200:
                    yield b"--frame\r\n"
                    yield b"Content-Type: image/jpeg\r\n\r\n"
                    yield resp.content
                    yield b"\r\n"
                time.sleep(0.1)  # 10 FPS polling
            except Exception as e:
                logging.warning(f"Snapshot stream error: {e}")
                time.sleep(1)
    else:
        # Continuous stream mode
        try:
            resp = session.get(url, timeout=5, stream=True)
            for chunk in resp.iter_content(chunk_size=1024):
                if chunk:
                    yield chunk
        except Exception as e:
            logging.error(f"Stream error: {e}")


@camera_bp.route("/stream.png")
@login_required
def stream_png():
    """Serve PNG snapshot from camera or group."""
    group = request.args.get("group")
    camera = request.args.get("camera")

    if group == "all":
        # Handle all cameras view
        pass
    elif camera:
        camera = validate_template_name(camera)
        if not camera:
            abort(400, "Invalid camera name")

    # Implementation would go here - this is a placeholder
    return Response(b"", mimetype="image/png")


@camera_bp.route("/test.mjpg", methods=["GET"])
@login_required
def test_mjpg():
    """Serve test MJPG stream."""
    group = request.args.get("group")
    camera = request.args.get("camera")

    if group == "all":
        # Handle all cameras view
        pass
    elif camera:
        camera = validate_template_name(camera)
        if not camera:
            abort(400, "Invalid camera name")

    def generate():
        # Test pattern generation
        yield b"--frame\r\n"
        yield b"Content-Type: image/jpeg\r\n\r\n"
        yield b"Test frame data\r\n"

    return Response(
        stream_with_context(generate()),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@camera_bp.route("/stream.mjpg", methods=["GET"])
@login_required
def stream_mjpg():
    """Serve live MJPG stream from camera."""
    group = request.args.get("group")
    camera = request.args.get("camera")

    if group == "all":
        # Handle all cameras view
        pass
    elif camera:
        camera = validate_template_name(camera)
        if not camera:
            abort(400, "Invalid camera name")

        # Get camera details and stream URL
        details = template_manager.get_template(camera)
        if not details:
            abort(404, "Camera not found")

        url = details.get("url")
        if not url:
            abort(400, "Camera URL not configured")

        return Response(
            stream_with_context(generate_live_stream(url)),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    abort(400, "Camera or group parameter required")


@camera_bp.route("/motion.mjpg", methods=["GET"])
@login_required
def motion_mjpg():
    """Serve MJPG stream with motion detection overlay."""
    group = request.args.get("group")
    camera = request.args.get("camera")

    if group == "all":
        # Handle all cameras view
        pass
    elif camera:
        camera = validate_template_name(camera)
        if not camera:
            abort(400, "Invalid camera name")

    def generate():
        # Motion detection overlay generation
        yield b"--frame\r\n"
        yield b"Content-Type: image/jpeg\r\n\r\n"
        yield b"Motion overlay frame data\r\n"

    return Response(
        stream_with_context(generate()),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@camera_bp.route("/caption.mjpg", methods=["GET"])
@login_required
def caption_mjpg():
    """Serve MJPG stream with AI captions overlay."""
    group = request.args.get("group")
    camera = request.args.get("camera")

    if group == "all":
        # Handle all cameras view
        pass
    elif camera:
        camera = validate_template_name(camera)
        if not camera:
            abort(400, "Invalid camera name")

    def generate():
        # Caption overlay generation
        yield b"--frame\r\n"
        yield b"Content-Type: image/jpeg\r\n\r\n"
        yield b"Caption overlay frame data\r\n"

    return Response(
        stream_with_context(generate()),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@camera_bp.route("/internal_caption.mjpg", methods=["GET"])
@login_required
def internal_caption_mjpg():
    """Serve internal MJPG stream with captions."""
    group = request.args.get("group")
    camera = request.args.get("camera")

    return Response(
        stream_with_context([]), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@camera_bp.route("/motion_caption.mjpg", methods=["GET"])
@login_required
def motion_caption_mjpg():
    """Serve MJPG stream with both motion detection and captions."""
    group = request.args.get("group")
    camera = request.args.get("camera")

    if group == "all":
        # Handle all cameras view
        pass
    elif camera:
        camera = validate_template_name(camera)
        if not camera:
            abort(400, "Invalid camera name")

    def generate():
        # Motion + caption overlay generation
        yield b"--frame\r\n"
        yield b"Content-Type: image/jpeg\r\n\r\n"
        yield b"Motion + caption overlay frame data\r\n"

    return Response(
        stream_with_context(generate()),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@camera_bp.route("/test_pattern.mjpg", methods=["GET"])
@login_required
def test_pattern_mjpg():
    """Serve test pattern MJPG stream."""

    def generate():
        spinner_frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        index = 0

        while True:
            # Generate test pattern frame
            yield b"--frame\r\n"
            yield b"Content-Type: image/jpeg\r\n\r\n"
            yield f"Test pattern {spinner_frames[index % len(spinner_frames)]}\r\n".encode()
            index += 1
            import time

            time.sleep(0.1)

    return Response(
        stream_with_context(generate()),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@camera_bp.route("/fast_stream.mjpg", methods=["GET"])
@login_required
def fast_stream_mjpg():
    """Serve fast MJPG stream for specific camera."""
    camera = request.args.get("camera")
    if not camera:
        abort(400, "camera parameter required")

    camera = validate_template_name(camera)
    if not camera:
        abort(400, "Invalid camera name")

    details = template_manager.get_template(camera)
    if not details:
        abort(404, "Camera not found")

    def generate():
        # Fast stream generation
        yield b"--frame\r\n"
        yield b"Content-Type: image/jpeg\r\n\r\n"
        yield b"Fast stream frame data\r\n"

    return Response(
        stream_with_context(generate()),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@camera_bp.route("/stream.mp4")
@login_required
def stream_mp4():
    """Stream the latest MP4 for a camera or group."""
    camera = request.args.get("camera")

    if camera:
        camera = validate_template_name(camera)
        if not camera:
            abort(400, "Invalid camera name")

    # Implementation for MP4 streaming
    return Response(b"", mimetype="video/mp4")


@camera_bp.route("/stream.m3u8")
@login_required
def playlist_m3u8():
    """Serve HLS playlist for camera streams."""
    path = os.path.join(os.path.dirname(os.path.join(__file__)), "..", VIDEO_DIRECTORY)

    # Implementation for HLS playlist
    return Response(b"", mimetype="application/vnd.apple.mpegurl")


@camera_bp.route("/stream")
@login_required
def stream():
    """Render the main streaming page."""
    # Get a list of active cameras (with updates within the last 1 day)
    return render_template("stream.html", page_title="Stream")


@camera_bp.route("/discover/scan_stream")
@login_required
def discover_cameras_scan_stream():
    """Stream camera discovery scan results."""

    def generate():
        cidr = request.args.get("cidr")
        nets = None

        # Camera discovery streaming implementation
        yield "data: Starting camera discovery...\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")
