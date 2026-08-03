import os


bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# The RAG retriever is kept in process memory, so one worker preserves the
# loaded-video state between /load_video and /ask requests.
workers = int(os.getenv("WEB_CONCURRENCY", "1"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
accesslog = "-"
errorlog = "-"
