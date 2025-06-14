# ABOUTME: Analysis blueprint for AI/LLM processing, captions, and summaries
# ABOUTME: Handles image analysis, natural language processing, and AI-powered insights

import json
import time

from flask import Blueprint, Response, abort, jsonify, request, stream_with_context

from app.blueprints.auth import login_required
from app.models import Summary
from app.utils.db import SessionLocal
from app.utils.llm import ask_question
from app.utils.validators import validate_template_name

analysis_bp = Blueprint("analysis", __name__)


@analysis_bp.route("/analyze/image", methods=["POST"])
@login_required
def analyze_image():
    """Analyze an image using AI/ML models."""
    if not request.is_json:
        abort(400, "JSON payload required")

    image_data = request.json.get("image_data")
    template_name = request.json.get("template_name")
    analysis_type = request.json.get("analysis_type", "caption")

    if not image_data:
        abort(400, "image_data required")

    if template_name:
        template_name = validate_template_name(template_name)
        if not template_name:
            abort(400, "Invalid template name")

    try:
        # Perform image analysis based on type
        if analysis_type == "caption":
            result = generate_image_caption(image_data)
        elif analysis_type == "objects":
            result = detect_objects(image_data)
        elif analysis_type == "motion":
            result = detect_motion(image_data)
        else:
            abort(400, "Invalid analysis_type")

        return jsonify(
            {
                "success": True,
                "analysis_type": analysis_type,
                "result": result,
                "template_name": template_name,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "message": f"Analysis failed: {str(e)}"}), 500


@analysis_bp.route("/caption/<string:template_name>", methods=["POST"])
@login_required
def generate_caption(template_name):
    """Generate AI caption for the latest image from a camera."""
    template_name = validate_template_name(template_name)
    if not template_name:
        abort(400, "Invalid template name")

    try:
        # Get latest image from template
        latest_image = get_latest_image(template_name)
        if not latest_image:
            return jsonify(
                {"success": False, "message": "No recent image available"}
            ), 404

        # Generate caption
        caption = generate_image_caption(latest_image)

        # Store caption in database
        session_db = SessionLocal()
        try:
            timestamp = int(time.time())
            summary = Summary(
                timestamp=timestamp,
                content=json.dumps(
                    {timestamp: f"Caption for {template_name}: {caption}"}
                ),
            )
            session_db.add(summary)
            session_db.commit()
        finally:
            session_db.close()

        return jsonify(
            {
                "success": True,
                "caption": caption,
                "template_name": template_name,
                "timestamp": timestamp,
            }
        )

    except Exception as e:
        return jsonify(
            {"success": False, "message": f"Caption generation failed: {str(e)}"}
        ), 500


@analysis_bp.route("/ask", methods=["POST"])
@login_required
def ask_llm():
    """Ask a question to the LLM about recent images or data."""
    if not request.is_json:
        abort(400, "JSON payload required")

    question = request.json.get("question")
    context = request.json.get("context", "")
    template_name = request.json.get("template_name")

    if not question:
        abort(400, "question required")

    if template_name:
        template_name = validate_template_name(template_name)
        if not template_name:
            abort(400, "Invalid template name")

    try:
        # Ask the LLM
        answer, truncated = ask_question(question, context)

        # Store Q&A in database
        session_db = SessionLocal()
        try:
            timestamp = int(time.time())

            # Store question
            session_db.add(
                Summary(
                    timestamp=timestamp,
                    content=json.dumps({timestamp: f"Q: {question}"}),
                )
            )

            # Store answer if available
            if answer:
                ts2 = timestamp + 1
                session_db.add(
                    Summary(
                        timestamp=ts2,
                        content=json.dumps({ts2: f"A: {answer}"}),
                    )
                )

            session_db.commit()
        finally:
            session_db.close()

        return jsonify(
            {
                "success": True,
                "question": question,
                "answer": answer,
                "truncated": truncated,
                "template_name": template_name,
            }
        )

    except Exception as e:
        return jsonify(
            {"success": False, "message": f"LLM query failed: {str(e)}"}
        ), 500


@analysis_bp.route("/summary/<string:template_name>", methods=["GET"])
@login_required
def get_summary(template_name):
    """Get AI-generated summary for a camera template."""
    template_name = validate_template_name(template_name)
    if not template_name:
        abort(400, "Invalid template name")

    # Get time range from query parameters
    hours = request.args.get("hours", "24", type=int)
    start_time = int(time.time()) - (hours * 3600)

    try:
        session_db = SessionLocal()
        try:
            # Get recent summaries/captions for this template
            summaries = (
                session_db.query(Summary)
                .filter(Summary.timestamp >= start_time)
                .order_by(Summary.timestamp.desc())
                .limit(100)
                .all()
            )

            summary_data = []
            for summary in summaries:
                try:
                    content = json.loads(summary.content)
                    summary_data.append(
                        {"timestamp": summary.timestamp, "content": content}
                    )
                except json.JSONDecodeError:
                    continue

            return jsonify(
                {
                    "success": True,
                    "template_name": template_name,
                    "hours": hours,
                    "summaries": summary_data,
                    "count": len(summary_data),
                }
            )

        finally:
            session_db.close()

    except Exception as e:
        return jsonify(
            {"success": False, "message": f"Failed to get summary: {str(e)}"}
        ), 500


@analysis_bp.route("/trends/<string:template_name>", methods=["GET"])
@login_required
def analyze_trends(template_name):
    """Analyze trends and patterns in camera data."""
    template_name = validate_template_name(template_name)
    if not template_name:
        abort(400, "Invalid template name")

    days = request.args.get("days", "7", type=int)
    start_time = int(time.time()) - (days * 24 * 3600)

    try:
        # Analyze trends in the data
        trends = {
            "activity_patterns": analyze_activity_patterns(template_name, start_time),
            "motion_trends": analyze_motion_trends(template_name, start_time),
            "caption_keywords": analyze_caption_keywords(template_name, start_time),
        }

        return jsonify(
            {
                "success": True,
                "template_name": template_name,
                "days": days,
                "trends": trends,
            }
        )

    except Exception as e:
        return jsonify(
            {"success": False, "message": f"Trend analysis failed: {str(e)}"}
        ), 500


@analysis_bp.route("/process/batch", methods=["POST"])
@login_required
def batch_process():
    """Process multiple images or data points in batch."""
    if not request.is_json:
        abort(400, "JSON payload required")

    items = request.json.get("items", [])
    process_type = request.json.get("process_type", "caption")

    if not items:
        abort(400, "items list required")

    results = []

    for item in items:
        try:
            if process_type == "caption":
                result = generate_image_caption(item.get("image_data"))
            elif process_type == "objects":
                result = detect_objects(item.get("image_data"))
            else:
                result = f"Unknown process_type: {process_type}"

            results.append(
                {"item_id": item.get("id"), "success": True, "result": result}
            )

        except Exception as e:
            results.append(
                {"item_id": item.get("id"), "success": False, "error": str(e)}
            )

    return jsonify(
        {
            "success": True,
            "process_type": process_type,
            "results": results,
            "processed": len(results),
        }
    )


@analysis_bp.route("/stream/analysis", methods=["GET"])
@login_required
def stream_analysis():
    """Stream real-time analysis results."""
    template_name = request.args.get("template_name")
    analysis_types = request.args.getlist("types") or ["caption"]

    if template_name:
        template_name = validate_template_name(template_name)
        if not template_name:
            abort(400, "Invalid template name")

    def generate():
        """Generate real-time analysis stream."""
        while True:
            try:
                # Get latest analysis results
                results = get_latest_analysis_results(template_name, analysis_types)

                if results:
                    yield f"data: {json.dumps(results)}\n\n"

                time.sleep(1)  # 1 second intervals

            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(5)  # 5 second delay on error

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


# Helper functions (these would be implemented with actual AI/ML models)
def generate_image_caption(image_data):
    """Generate caption for image data."""
    # Placeholder implementation
    return "AI-generated caption for the image"


def detect_objects(image_data):
    """Detect objects in image data."""
    # Placeholder implementation
    return ["person", "car", "tree"]


def detect_motion(image_data):
    """Detect motion in image data."""
    # Placeholder implementation
    return {"motion_detected": True, "confidence": 0.85}


def get_latest_image(template_name):
    """Get the latest image for a template."""
    # Placeholder implementation
    return "base64_image_data"


def analyze_activity_patterns(template_name, start_time):
    """Analyze activity patterns."""
    # Placeholder implementation
    return {"peak_hours": [9, 17], "quiet_hours": [1, 6]}


def analyze_motion_trends(template_name, start_time):
    """Analyze motion trends."""
    # Placeholder implementation
    return {"average_motion": 0.3, "trend": "increasing"}


def analyze_caption_keywords(template_name, start_time):
    """Analyze common keywords in captions."""
    # Placeholder implementation
    return {"top_keywords": ["person", "car", "outdoor"], "sentiment": "neutral"}


def get_latest_analysis_results(template_name, analysis_types):
    """Get latest analysis results for streaming."""
    # Placeholder implementation
    return {
        "timestamp": int(time.time()),
        "template_name": template_name,
        "results": {type_: f"Latest {type_} result" for type_ in analysis_types},
    }
