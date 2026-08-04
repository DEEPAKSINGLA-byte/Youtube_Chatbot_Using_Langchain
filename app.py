import logging
import os
import re
from urllib.parse import parse_qs, urlparse

from flask import Flask, jsonify, render_template, request

from config import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from rag import ask_question, load_video

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

YOUTUBE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")


def get_requested_language(data):
    """Return a supported language code from request JSON."""
    language = data.get("language", DEFAULT_LANGUAGE)

    if language not in SUPPORTED_LANGUAGES:
        return None

    return language


def extract_youtube_video_id(value):
    """Return a YouTube video ID from a URL or raw 11-character ID."""
    youtube_url = str(value).strip()

    if YOUTUBE_ID_PATTERN.fullmatch(youtube_url):
        return youtube_url

    youtube_hosts = (
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
    )

    if "://" not in youtube_url and youtube_url.lower().startswith(youtube_hosts):
        youtube_url = f"https://{youtube_url}"

    parsed_url = urlparse(youtube_url)
    host = parsed_url.netloc.lower().removeprefix("www.")
    path_parts = [part for part in parsed_url.path.split("/") if part]

    if host in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
        query_video_id = parse_qs(parsed_url.query).get("v", [""])[0]

        if YOUTUBE_ID_PATTERN.fullmatch(query_video_id):
            return query_video_id

        if len(path_parts) >= 2 and path_parts[0] in {"embed", "shorts", "live"}:
            candidate = path_parts[1]

            if YOUTUBE_ID_PATTERN.fullmatch(candidate):
                return candidate

    if host == "youtu.be" and path_parts:
        candidate = path_parts[0]

        if YOUTUBE_ID_PATTERN.fullmatch(candidate):
            return candidate

    return None


@app.route("/")
def home():
    """Show the chatbot page."""
    return render_template("index.html")


@app.route("/load_video", methods=["POST"])
def load_video_route():
    """Fetch one YouTube transcript and prepare it for questions."""
    data = request.get_json(silent=True) or {}
    youtube_url = str(data.get("youtube_url", data.get("video_id", "")) or "").strip()
    video_id = extract_youtube_video_id(youtube_url)
    language = get_requested_language(data)

    if not youtube_url:
        return jsonify({"error": "Please paste a YouTube URL."}), 400

    if video_id is None:
        return jsonify({"error": "Please paste a valid YouTube URL."}), 400

    if language is None:
        return jsonify({"error": "Please select a supported language."}), 400

    logger.info("Loading video transcript for video_id=%s language=%s", video_id, language)
    result = load_video(video_id, language)

    if result.get("status") != "success":
        logger.warning("Failed to load video_id=%s: %s", video_id, result.get("message"))
        return jsonify({"error": result.get("message")}), 400

    result["video_id"] = video_id
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
