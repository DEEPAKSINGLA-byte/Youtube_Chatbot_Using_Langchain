# YouTube LangChain RAG Chatbot

This is a web application that allows you to "chat" with any YouTube video. It fetches the video's transcript, processes the text using LangChain, and uses an AI model (via the Groq API) to answer your questions based strictly on the video's content.

## Key Features

*   **Robust Transcript Fetching:** Uses a custom HTTP session with browser headers (`User-Agent`) to prevent YouTube from prematurely dropping the connection (`ChunkedEncodingError`).
*   **Intelligent Text Chunking:** Uses LangChain's `RecursiveCharacterTextSplitter` to intelligently break down long 2-hour transcripts into readable paragraphs and sentences, ensuring the AI gets complete context without cutting words in half.
*   **Fast Retrieval Augmented Generation (RAG):** Uses an in-memory vector database (FAISS) and Sentence Transformers (`all-MiniLM-L6-v2`) to quickly find the exact moments in the video relevant to your question.
*   **Powered by Groq:** Uses the ultra-fast Groq API for the Large Language Model (LLM) processing.
*   **Docker Ready:** Can be instantly containerized and shared via `.tar` files.

---

## Project Architecture (How it Works)

1.  **Extract Video ID:** The Flask backend (`app.py`) parses the YouTube URL provided by the user.
2.  **Fetch Transcript:** The `rag.py` file uses `youtube-transcript-api` to pull the captions. A custom `User-Agent` is used to mimic a real browser to bypass YouTube's bot-protection.
3.  **Split Text:** Because LLMs have a token limit, the transcript is fed into a `RecursiveCharacterTextSplitter`. This breaks the text down intelligently (trying double-newlines, then single-newlines, then spaces) to keep semantic meaning intact.
4.  **Vector Store:** The chunks are converted into mathematical embeddings and stored in FAISS (a local, temporary vector database).
5.  **Answering:** When you ask a question, the app finds the most relevant transcript chunks, packages them into a prompt, and sends them to the Groq LLM to generate a natural answer.

---

## Local Setup Instructions

### Prerequisites
*   Python 3.11+
*   A free API key from [Groq Console](https://console.groq.com/).

### 1. Install Dependencies
Open your terminal in the project directory and run:
```bash
# (Optional but recommended) Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the required packages
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a file named `.env` in the root folder (you can copy `.env.example` if it exists) and add your Groq API key:
```env
GROQ_API_KEY="your_groq_api_key_here"
```

### 3. Run the App
```bash
python app.py
```
*The app will be available at `http://localhost:5000` or whatever port is configured.*

---

## Docker Guide

If you prefer to run or share the app using Docker, follow these steps:

### Building the Image
To build the Docker image, run this command in the same directory as your `Dockerfile`:
```bash
docker build -t youtube-rag-bot .
```
> **Note on Docker Caching:** Docker is smart! If you only change `rag.py` or `app.py`, the rebuild will take just a few seconds and use **0 MB of internet data**. However, if you add a new library to `requirements.txt`, Docker will automatically invalidate the cache and spend a few minutes re-downloading the Python packages.

### Running the Container
```bash
docker run -p 5000:5000 --env-file .env youtube-rag-bot
```

### Sharing the App (Exporting to `.tar`)
If you need to move the built Docker image to another computer or server without using Docker Hub, you can save it as a `.tar` file:
```bash
# This creates a file named 'youtube-rag-bot.tar' in your folder
docker save -o youtube-rag-bot.tar youtube-rag-bot
```
To load it on the other computer, they just run:
```bash
docker load -i youtube-rag-bot.tar
```
