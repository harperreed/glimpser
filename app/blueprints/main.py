# ABOUTME: Main blueprint for core application routes like home, help, and navigation
# ABOUTME: Contains the primary user interface routes and basic functionality

from flask import Blueprint, abort, render_template, request

from app.blueprints.auth import login_required
from app.utils import template_manager
from app.utils.settings_tooltips import SETTINGS_GROUPS
from app.utils.validators import validate_template_name

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def index():
    """Render the main dashboard page."""
    templates = template_manager.get_templates()
    return render_template("index.html", template_details=templates)


@main_bp.route("/help")
@login_required
def help_page():
    """Render the help page."""
    return render_template("help.html")


@main_bp.route("/docs/<string:filename>")
@login_required
def docs(filename):
    """Serve documentation files."""
    return render_template("docs.html", filename=filename)


@main_bp.route("/cli_help")
@login_required
def cli_help():
    """Render CLI help page."""
    return render_template("cli_help.html")


@main_bp.route("/settings_help")
@login_required
def settings_help():
    """Render settings help page."""
    return render_template("settings_help.html", settings_groups=SETTINGS_GROUPS)


@main_bp.route("/offline")
@login_required
def offline():
    """Render offline page."""
    return render_template("offline.html")


@main_bp.route("/group/<string:group_name>")
@login_required
def group_view(group_name):
    """Render view for a specific template group."""
    templates = template_manager.get_templates()
    group_templates = {
        name: details
        for name, details in templates.items()
        if details.get("group") == group_name
    }
    return render_template(
        "group.html", group_name=group_name, template_details=group_templates
    )


@main_bp.route("/live")
@login_required
def live():
    """Render the live view page."""
    camera = request.args.get("camera")
    if camera:
        camera = validate_template_name(camera)
        if camera is None:
            abort(400, "Invalid camera name")
        details = template_manager.get_template(camera)
        if not details:
            abort(404)
        templates = {camera: details}
    else:
        templates = template_manager.get_templates()

    return render_template(
        "live.html", template_details=templates, page_title="Live View"
    )


@main_bp.route("/clock")
@login_required
def clock_page():
    """Render a standalone clock page."""
    return render_template("clock.html", page_title="Clock")
