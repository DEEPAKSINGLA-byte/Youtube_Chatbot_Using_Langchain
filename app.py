import logging
import os

from flask import Flask, jsonify, render_template, request

from config import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from rag import ask_question, load_video

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def get_requested_language(data):
    """Return a supported language code from request JSON."""
    language = data.get("language", DEFAULT_LANGUAGE)

    if language not in SUPPORTED_LANGUAGES:
        return None

    return language


@app.route("/")
def home():
    """Show the chatbot page."""
    return render_template("index.html")


@app.route("/load_video", methods=["POST"])
def load_video_route():
    """Load one YouTube video and prepare it for questions."""
    data = request.get_json(silent=True) or {}
    video_id = data.get("video_id", "").strip()
    language = get_requested_language(data)

    if not video_id:
        return jsonify({"error": "Please enter a video ID."}), 400

    if language is None:
        return jsonify({"error": "Please select a supported language."}), 400

    logger.info("Loading video transcript for video_id=%s language=%s", video_id, language)
    result = load_video(video_id, language)

    if result.get("status") != "success":
        logger.warning("Failed to load video_id=%s: %s", video_id, result.get("message"))
        return jsonify({"error": result.get("message")}), 400

    logger.info("Loaded video_id=%s with %s chunks", video_id, result.get("chunks"))
    return jsonify(result)


@app.route("/ask", methods=["POST"])
def ask_route():
    """Answer a question using the video that is already loaded."""
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    language = get_requested_language(data)

    if not question:
        return jsonify({"error": "Please enter a question."}), 400

    if language is None:
        return jsonify({"error": "Please select a supported language."}), 400

    logger.info("Answering question with %s characters language=%s", len(question), language)
    result = ask_question(question, language)
    return jsonify(result)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG") == "1",
    )
