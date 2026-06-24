"""
app/routes/health.py
----------------------
GET /health
Returns connection status for each service the frontend status panel displays.

Shape expected by script.js:
  { "status": "ok", "vertex": "connected", "bigquery": "connected", "mcp": "connected" }

Any value other than "connected" makes the dot go red in the UI.
"""

from fastapi import APIRouter
from app.mcp.client import BigQueryMCPClient
from app.services.vertex import get_genai_client
from app.utils.logger import get_logger

logger = get_logger(__name__)

health_router = APIRouter()


@health_router.get("/health")
async def health():
    result = {
        "status": "ok",
        "vertex": "disconnected",
        "bigquery": "disconnected",
        "mcp": "disconnected",
    }

    # Check Vertex AI (genai client initialises without a network call,
    # so a successful import + instantiation is enough to mark it live)
    try:
        get_genai_client()
        result["vertex"] = "connected"
    except Exception as e:
        logger.warning(f"Vertex AI health check failed: {e}")

    # Check BigQuery MCP server (open a session, list tools, close)
    try:
        async with BigQueryMCPClient() as mcp_client:
            tools = await mcp_client.list_tools()
            if tools:
                result["bigquery"] = "connected"
                result["mcp"] = "connected"
    except Exception as e:
        logger.warning(f"BigQuery/MCP health check failed: {e}")

    if any(v == "disconnected" for v in result.values() if v != result["status"]):
        result["status"] = "degraded"

    return result
