"""
FastAPI backend for the AI E-commerce Product Scout.

Initializes the ADK Agent and exposes a POST /chat endpoint
for the Streamlit frontend to communicate with.
"""

import os
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env BEFORE importing modules that need env vars at init time
load_dotenv()

import db
import agent_config

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup and shutdown logic."""
    # Startup
    logger.info("🚀 Starting AI E-commerce Product Scout backend...")
    try:
        if db.check_connection():
            logger.info("✅ Database connection verified.")
        else:
            logger.warning("⚠️  Database is not reachable — the app will start but queries will fail.")
    except Exception as e:
        logger.warning("⚠️  Could not verify database connection: %s", e)

    yield

    # Shutdown
    logger.info("🛑 Shutting down backend...")
    db.close_pool()


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI E-commerce Product Scout",
    description="An AI-powered shopping assistant backed by Google ADK and AlloyDB.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Streamlit and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:8501",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Incoming chat message from the frontend."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's message to the shopping assistant.",
        examples=["Show me wireless headphones under $100"],
    )
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique session identifier. Omit to start a new session.",
    )


class ChatResponse(BaseModel):
    """Response from the shopping assistant."""

    response: str = Field(
        ...,
        description="The assistant's reply.",
    )
    session_id: str = Field(
        ...,
        description="The session ID (echoed back for tracking).",
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    database: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Send a message to the AI Shopping Assistant and get a response.

    The assistant uses Gemini 1.5 Flash via Google ADK and queries the
    AlloyDB product catalog using natural language.
    """
    try:
        logger.info(
            "Chat request — session=%s, message=%s",
            request.session_id,
            request.message[:80],
        )

        response_text = await agent_config.chat(
            session_id=request.session_id,
            user_message=request.message,
        )

        return ChatResponse(
            response=response_text,
            session_id=request.session_id,
        )

    except Exception as e:
        logger.error("Error processing chat request: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your request: {str(e)}",
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for Cloud Run.

    Verifies the service is running and checks database connectivity.
    """
    db_healthy = db.check_connection()
    return HealthResponse(
        status="healthy",
        database="connected" if db_healthy else "unreachable",
    )


@app.get("/")
async def root():
    """Root endpoint — redirect info."""
    return {
        "service": "AI E-commerce Product Scout",
        "version": "1.0.0",
        "docs": "/docs",
        "chat_endpoint": "POST /chat",
        "health": "/health",
    }
