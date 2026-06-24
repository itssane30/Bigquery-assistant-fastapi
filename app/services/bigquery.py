"""
app/services/bigquery.py
---------------------------
IMPORTANT: in this architecture, the /chat flow never calls BigQuery
directly - all SQL execution happens through the BigQuery MCP server
(see app/mcp/client.py). This module exists ONLY so /health can do a
fast, independent sanity check that the configured credentials can
actually reach BigQuery, without paying for a full MCP round trip.

This file never talks to Gemini.
"""

from google.cloud import bigquery

from app.config import Config
from app.utils.logger import get_logger

logger = get_logger(__name__)


def check_bigquery_connection() -> bool:
    """Lightweight credential/connectivity check - not used by /chat."""
    try:
        client = bigquery.Client(project=Config.PROJECT_ID)
        # list_datasets() is cheap; max_results=1 keeps it fast even if
        # the project has many datasets.
        next(iter(client.list_datasets(max_results=1)), None)
        return True
    except Exception as exc:
        logger.warning(f"BigQuery health check failed: {exc}")
        return False
