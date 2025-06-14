# ABOUTME: Blueprint registry for registering all application blueprints with Flask app
# ABOUTME: Replaces the monolithic init_routes function with modular blueprint registration

from flask import Flask

from app.blueprints.admin import admin_bp
from app.blueprints.analysis import analysis_bp
from app.blueprints.api import api_bp
from app.blueprints.auth import auth_bp
from app.blueprints.camera import camera_bp
from app.blueprints.capture import capture_bp
from app.blueprints.main import main_bp


def register_blueprints(app: Flask) -> None:
    """Register all application blueprints with the Flask app."""

    # Register blueprints with URL prefixes where appropriate
    app.register_blueprint(auth_bp)  # No prefix for auth routes
    app.register_blueprint(main_bp)  # No prefix for main routes
    app.register_blueprint(camera_bp)  # No prefix for camera routes
    app.register_blueprint(capture_bp)  # No prefix for capture routes
    app.register_blueprint(analysis_bp)  # No prefix for analysis routes
    app.register_blueprint(admin_bp)  # No prefix for admin routes
    app.register_blueprint(api_bp)  # /api prefix for API routes

    # Add security headers to all responses
    @app.after_request
    def add_security_headers(response):
        """Add common security headers to every response."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.before_request
    def enforce_host_domain():
        """Block requests missing a domain when enforcement is enabled."""
        from flask import abort, request

        from app.config import ENFORCE_DOMAIN_IN_HOST

        if ENFORCE_DOMAIN_IN_HOST:
            host = request.headers.get("Host", "")
            if "." not in host:
                abort(403)

    @app.context_processor
    def inject_footer_data():
        """Inject common template variables."""
        from app.config import (
            CHYRON_SPEED,
            CLOCK_DIGITAL,
            CLOCK_NAVBAR,
            CLOCK_OVERLAY,
            HEALTH_STATUS_ALWAYS_VISIBLE,
            NAV_ICON,
            VERSION,
        )

        # Check for updates
        outdated = False
        try:
            from app.utils.git import get_commit_hash
            from app.utils.github import is_update_available

            outdated = is_update_available(str(VERSION))
            commit_hash = get_commit_hash()
        except Exception:
            commit_hash = "unknown"

        # Get NODE_ENV
        import os

        node_env = os.environ.get("NODE_ENV", "production")

        return dict(
            VERSION=VERSION,
            VERSION_OUTDATED=outdated,
            COMMIT_HASH=commit_hash,
            NODE_ENV=node_env,
            CHYRON_SPEED=CHYRON_SPEED,
            NAV_ICON=NAV_ICON,
            HEALTH_STATUS_ALWAYS_VISIBLE=HEALTH_STATUS_ALWAYS_VISIBLE,
            CLOCK_OVERLAY=CLOCK_OVERLAY,
            CLOCK_DIGITAL=CLOCK_DIGITAL,
            CLOCK_NAVBAR=CLOCK_NAVBAR,
        )
