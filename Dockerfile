FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

# FIX: Upgrade pip first to prevent the hash mismatch error
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Force HuggingFace to download the model during the build
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
