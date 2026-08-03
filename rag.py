"""RAG helpers for loading a YouTube transcript and answering questions."""
import logging
import os

from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DEFAULT_LANGUAGE,
    EMBEDDING_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    SUPPORTED_LANGUAGES,
    TEMPERATURE,
    TOP_K,
)

logger = logging.getLogger(__name__)

BROKEN_LOCAL_PROXY = "http://127.0.0.1:9"

retriever = None
llm = None
loaded_video_id = None
loaded_video_metadata = None


def load_video(video_id, language=DEFAULT_LANGUAGE):
    """Prepare a video's transcript so the chatbot can answer questions."""
    global loaded_video_id, loaded_video_metadata, retriever

    clear_broken_proxy_settings()

    if language not in SUPPORTED_LANGUAGES:
        return {
            "status": "error",
            "message": "Please select a supported language.",
        }

    cache_key = (video_id, language)

    if retriever is not None and loaded_video_id == cache_key:
        logger.info("Using cached retriever for video_id=%s language=%s", video_id, language)
        return loaded_video_metadata

    try:
        transcript = get_transcript_text(video_id, language)
    except TranscriptsDisabled:
        logger.warning("Captions are disabled for video_id=%s", video_id)
        return {
            "status": "error",
            "message": "No captions are available for this video.",
        }
    except Exception as error:
        logger.exception(
            "Failed to load transcript for video_id=%s language=%s",
            video_id,
            language,
        )
        return {
            "status": "error",
            "message": f"An error occurred: {error}",
        }

    chunks = split_transcript(transcript)
    logger.info(
        "Split transcript for video_id=%s language=%s into %s chunks",
        video_id,
        language,
        len(chunks),
    )

    from langchain_huggingface import HuggingFaceEmbeddings

    logger.info("Building embeddings with model=%s", EMBEDDING_MODEL)
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vector_store = FAISS.from_documents(chunks, embeddings)

    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": TOP_K},
    )

    loaded_video_id = cache_key
    loaded_video_metadata = {
        "status": "success",
        "message": "Video processed successfully.",
        "chunks": len(chunks),
        "embedding_model": EMBEDDING_MODEL,
        "language": language,
        "language_name": SUPPORTED_LANGUAGES[language],
    }

    logger.info("Video processed successfully for video_id=%s language=%s", video_id, language)
    return loaded_video_metadata


def ask_question(question, language=DEFAULT_LANGUAGE):
    """Answer a question using the retriever created by load_video()."""
    if retriever is None:
        return {
            "answer": "Please load a video first.",
            "sources": [],
        }

    if language not in SUPPORTED_LANGUAGES:
        return {
            "answer": "Please select a supported language.",
            "sources": [],
        }

    if loaded_video_id and loaded_video_id[1] != language:
        return {
            "answer": f"Please reload the video in {SUPPORTED_LANGUAGES[language]} first.",
            "sources": [],
        }

    main_chain = build_question_chain(language)
    try:
        response = main_chain.invoke(question)
    except RuntimeError as error:
        logger.warning("Could not answer question: %s", error)
        return {
            "answer": str(error),
            "sources": [],
        }
    except Exception:
        logger.exception("Failed to answer question")
        return {
            "answer": "An error occurred while answering the question.",
            "sources": [],
        }

    docs = response["context"]
    sources = [doc.page_content for doc in docs]

    return {
        "answer": response["answer"],
        "sources": sources,
    }


def get_transcript_text(video_id, language=DEFAULT_LANGUAGE):
    """Download a transcript in the selected language and turn it into plain text."""
    clear_broken_proxy_settings()

    youtube = YouTubeTranscriptApi()
    transcript_list = youtube.list(video_id)

    try:
        transcript = transcript_list.find_transcript([language])
    except NoTranscriptFound:
        if language == DEFAULT_LANGUAGE:
            raise

        transcript = transcript_list.find_transcript([DEFAULT_LANGUAGE]).translate(language)
        logger.info(
            "Using translated transcript for video_id=%s from=%s to=%s",
            video_id,
            DEFAULT_LANGUAGE,
            language,
        )

    transcript_parts = transcript.fetch()
    logger.info("Fetched transcript for video_id=%s language=%s", video_id, language)

    return " ".join(part.text for part in transcript_parts)


def clear_broken_proxy_settings():
    """Remove the local dummy proxy that prevents outbound HTTPS requests."""
    proxy_keys = (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    )

    for key in proxy_keys:
        if os.environ.get(key) == BROKEN_LOCAL_PROXY:
            os.environ.pop(key)
            logger.info("Removed broken proxy environment variable: %s", key)


def split_transcript(transcript):
    """Break the transcript into chunks that are easier to search."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    return splitter.create_documents([transcript])


def build_question_chain(language=DEFAULT_LANGUAGE):
    """Build the LangChain pipeline that retrieves context and calls the LLM."""
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import (
        RunnableLambda,
        RunnableParallel,
        RunnablePassthrough,
    )

    language_name = SUPPORTED_LANGUAGES.get(language, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])
    system_prompt = (
        "You are a helpful assistant. Use the following pieces of retrieved video "
        "transcript to answer the question. If you don't know the answer, just say "
        f"that you don't know. Answer in {language_name}. \n\n"
        "Context: {context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    retrieve_context = RunnableParallel({
        "context": retriever,
        "input": RunnablePassthrough(),
    })

    answer_chain = (
        RunnablePassthrough.assign(
            formatted_context=lambda inputs: format_docs(inputs["context"])
        )
        | RunnableLambda(
            lambda inputs: {
                "context": inputs["formatted_context"],
                "input": inputs["input"],
            }
        )
        | prompt
        | get_llm()
        | StrOutputParser()
    )

    return retrieve_context | RunnablePassthrough.assign(answer=answer_chain)


def get_llm():
    """Create the LLM once, then reuse it for later questions."""
    global llm

    if llm is None:
        from langchain_groq import ChatGroq

        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is missing. Add it to your .env file.")

        logger.info("Initializing Groq chat model=%s", GROQ_MODEL)
        llm = ChatGroq(
            model=GROQ_MODEL,
            temperature=TEMPERATURE,
            api_key=GROQ_API_KEY,
        )

    return llm


def format_docs(retrieved_docs):
    """Convert retrieved LangChain documents into one context string."""
    return "\n\n".join(doc.page_content for doc in retrieved_docs)
