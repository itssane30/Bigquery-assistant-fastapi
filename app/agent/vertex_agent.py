"""
app/agent/vertex_agent.py
----------------------------
This is the heart of the application (your Phase 9):

    Receive user question
        |
    Ask Gemini
        |
    Gemini calls tool
        |
    MCP executes
        |
    Gemini receives data
        |
    Gemini summarizes
        |
    Return response
"""

import time
from google.genai import types

from app.agent.reasoning import run_agent_loop
from app.config import Config
from app.mcp.bigquery_tools import mcp_tools_to_gemini_declarations
from app.mcp.client import BigQueryMCPClient
from app.prompts.system_prompt import build_system_prompt
from app.services.vertex import get_genai_client
from app.utils.logger import get_logger

logger = get_logger(__name__)

_SQL_ARG_KEYS = ("query", "sql", "sql_query", "statement")


def _extract_sql(trace: list[dict]) -> str | None:
    """Best-effort pull of the SQL that was actually run, for the API response.

    We don't hardcode one parameter name because it depends on the live
    schema the MCP server advertises for its query-execution tool.
    """
    for step in reversed(trace):
        for key in _SQL_ARG_KEYS:
            if key in step.get("args", {}):
                return step["args"][key]
    return None


async def answer_question(question: str) -> dict:
    """Runs one full question through the agent and returns a structured result."""
    start = time.time()
    client = get_genai_client()

    async with BigQueryMCPClient() as mcp_client:
        mcp_tools = await mcp_client.list_tools()
        logger.info(f"BigQuery MCP server advertised tools: {[t.name for t in mcp_tools]}")

        gemini_tool = types.Tool(function_declarations=mcp_tools_to_gemini_declarations(mcp_tools))

        config = types.GenerateContentConfig(
            tools=[gemini_tool],
            system_instruction=build_system_prompt(),
            temperature=0.2,
        )

        contents = [types.Content(role="user", parts=[types.Part.from_text(text=question)])]

        answer_text, trace = await run_agent_loop(
            client=client,
            model=Config.MODEL,
            contents=contents,
            config=config,
            mcp_client=mcp_client,
        )

    return {
        "answer": answer_text,
        "sql": _extract_sql(trace),
        "tool_calls": trace,
        "execution_time_sec": round(time.time() - start, 2),
    }
