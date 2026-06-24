"""
app/mcp/client.py
-------------------
Native MCP client for Google's managed BigQuery Remote MCP Server.

  Server:    https://bigquery.googleapis.com/mcp
  Transport: MCP Streamable HTTP
  Auth:      OAuth2 Bearer token, scope https://www.googleapis.com/auth/bigquery
             (API keys are NOT supported by this server)

This module only speaks MCP. It never imports google-cloud-bigquery and
never builds SQL itself - it just opens a session, lists whatever tools
the server advertises, and executes whichever one the agent asks for.
That's what keeps this swappable: point BIGQUERY_MCP_URL at a different
MCP server (e.g. a self-hosted MCP Toolbox instance) later and nothing
above this layer needs to change.
"""

from __future__ import annotations

import google.auth
import google.auth.transport.requests
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app.config import Config
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Cached so we don't re-read the service-account key (or hit the metadata
# server) on every single call - we only refresh the token, not the
# credential object itself.
_credentials = None


def _get_access_token() -> str:
    """Mints/refreshes an OAuth2 access token scoped for BigQuery.

    Works transparently with either a service-account key file
    (GOOGLE_APPLICATION_CREDENTIALS) or `gcloud auth application-default
    login` - google.auth.default() picks whichever is configured.
    """
    global _credentials
    if _credentials is None:
        _credentials, _ = google.auth.default(scopes=Config.BIGQUERY_SCOPES)

    if not _credentials.valid:
        _credentials.refresh(google.auth.transport.requests.Request())

    return _credentials.token


class BigQueryMCPClient:
    """Async context manager wrapping one MCP session against the BigQuery MCP server.

    Usage:
        async with BigQueryMCPClient() as mcp_client:
            tools = await mcp_client.list_tools()
            result_text = await mcp_client.call_tool("execute_sql", {"query": "..."})
    """

    def __init__(self, url: str | None = None):
        self.url = url or Config.BIGQUERY_MCP_URL
        self._streams_cm = None
        self._session_cm = None
        self.session: ClientSession | None = None

    async def __aenter__(self) -> "BigQueryMCPClient":
        token = _get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            # Tells Google which project to bill/attribute the BigQuery
            # job to - required for execute_sql to work.
            "x-goog-user-project": Config.PROJECT_ID,
        }

        self._streams_cm = streamablehttp_client(self.url, headers=headers)
        read_stream, write_stream, _ = await self._streams_cm.__aenter__()

        self._session_cm = ClientSession(read_stream, write_stream)
        self.session = await self._session_cm.__aenter__()
        await self.session.initialize()

        logger.info(f"Connected to BigQuery MCP server at {self.url}")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._session_cm is not None:
            await self._session_cm.__aexit__(exc_type, exc, tb)
        if self._streams_cm is not None:
            await self._streams_cm.__aexit__(exc_type, exc, tb)

    async def list_tools(self) -> list:
        """Returns the live list of MCP Tool objects the server advertises."""
        result = await self.session.list_tools()
        return result.tools

    async def call_tool(self, name: str, arguments: dict) -> str:
        """Executes one MCP tool call and returns its text content."""
        result = await self.session.call_tool(name, arguments)

        # MCP responses contain blocks (TextBlock, ImageBlock, ResourceBlock etc.)
        texts = [block.text for block in result.content if hasattr(block, "text")]
        text = "\n".join(texts) if texts else str(result.content)

        if getattr(result, "isError", False):
            logger.warning(f"MCP tool '{name}' returned an error: {text}")

        return text
