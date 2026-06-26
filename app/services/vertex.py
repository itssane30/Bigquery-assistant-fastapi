"""
app/services/vertex.py
------------------------
Responsibilities, and nothing else:
  1. Initialize the Vertex AI backed Gemini client (google-genai SDK)
  2. Return new client instances on demand to avoid shared async state across requests
"""

from google import genai
from google.genai.client import AsyncClient
from google.genai import types

from app.config import Config


def build_genai_client() -> genai.Client:
    """Create a fresh google-genai Client configured for Vertex AI."""
    return genai.Client(
        vertexai=True,
        project=Config.PROJECT_ID,
        location=Config.LOCATION,
        http_options=types.HttpOptions(
            retryOptions=types.HttpRetryOptions(
                attempts=5,
                initialDelay=1.0,
                maxDelay=20.0,
                expBase=2.0,
                jitter=0.2,
                httpStatusCodes=[429, 500, 502, 503, 504],
            ),
        ),
    )


def get_genai_client() -> genai.Client:
    """Return a new google-genai Client configured for Vertex AI."""
    return build_genai_client()


def get_genai_async_client() -> AsyncClient:
    """Return a fresh async google-genai client for request-scoped use."""
    return build_genai_client().aio
