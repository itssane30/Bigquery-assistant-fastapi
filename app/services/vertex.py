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


class GenaiAsyncClient:
    """Request-scoped async client wrapper that keeps the sync client alive.

    The google-genai SDK stores shared state in the sync `Client` object, and
    the async wrapper depends on it. If the sync client is garbage collected
    too early, its destructor may close shared resources while the async
    client is still in use.
    """

    def __init__(self, client: genai.Client):
        self._client = client
        self._aio = client.aio

    async def __aenter__(self) -> AsyncClient:
        return self._aio

    async def __aexit__(self, exc_type, exc, tb) -> None:
        try:
            await self._aio.aclose()
        finally:
            self._client.close()

    def __getattr__(self, name):
        return getattr(self._aio, name)


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


def get_genai_async_client() -> GenaiAsyncClient:
    """Return a fresh async google-genai client for request-scoped use."""
    return GenaiAsyncClient(build_genai_client())
