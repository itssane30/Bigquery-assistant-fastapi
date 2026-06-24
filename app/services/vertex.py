"""
app/services/vertex.py
------------------------
Responsibilities, and nothing else:
  1. Initialize the Vertex AI backed Gemini client (google-genai SDK)
  2. Return that client instance (cached as a singleton)
"""

from google import genai

from app.config import Config

_client: genai.Client | None = None


def get_genai_client() -> genai.Client:
    """Returns a singleton google-genai Client configured for Vertex AI."""
    global _client
    if _client is None:
        _client = genai.Client(
            vertexai=True,
            project=Config.PROJECT_ID,
            location=Config.LOCATION,
        )
    return _client
