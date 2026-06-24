"""
app/agent/reasoning.py
-------------------------
The agent loop, exactly as in your Phase 10 pseudocode:

    while True:
        send prompt
        model asks for tool
        execute MCP tool
        append response
        continue
        until model returns text

Because the BigQuery MCP tools are discovered live (not local Python
functions), this is a *manual* function-calling loop rather than the SDK's
automatic one: we have to take each function_call the model produces,
execute it ourselves against the MCP session, and feed the result back.
"""

from __future__ import annotations
import time

from google import genai
from google.genai import types

from app.config import Config
from app.mcp.client import BigQueryMCPClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def run_agent_loop(
    client: genai.Client,
    model: str,
    contents: list[types.Content],
    config: types.GenerateContentConfig,
    mcp_client: BigQueryMCPClient,
    max_steps: int = Config.MAX_AGENT_STEPS,
) -> tuple[str, list[dict]]:
    """Runs the send -> tool-call -> execute -> repeat loop until the model answers in text.

    Returns (answer_text, trace) where trace is a list of every tool call
    made along the way (tool name, arguments, elapsed time, and a preview
    of the result) - useful for debugging and for returning to the client
    for transparency.
    """
    trace: list[dict] = []

    for step in range(max_steps):
        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0]
        parts = candidate.content.parts or []
        function_calls = [p.function_call for p in parts if p.function_call]

        if not function_calls:
            return response.text, trace

        # Record the model's tool-call turn in the running conversation.
        contents.append(candidate.content)

        response_parts = []
        for fc in function_calls:
            args = dict(fc.args) if fc.args else {}
            logger.info(f"[step {step}] model called {fc.name}({args})")

            t0 = time.time()
            try:
                result_text = await mcp_client.call_tool(fc.name, args)
                error = None
            except Exception as exc:  # surfaced back to the model so it can self-correct
                result_text = ""
                error = str(exc)
                logger.warning(f"Tool call {fc.name} failed: {error}")

            elapsed = round(time.time() - t0, 3)
            trace.append(
                {
                    "tool": fc.name,
                    "args": args,
                    "elapsed_sec": elapsed,
                    "error": error,
                    "result_preview": (result_text or error or "")[:2000],
                }
            )

            response_parts.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response={"result": result_text} if not error else {"error": error},
                )
            )

        contents.append(types.Content(role="user", parts=response_parts))

    logger.warning(f"Agent loop hit max_steps={max_steps} without a final answer")
    return (
        "I wasn't able to finish the analysis within the allotted steps. "
        "Try asking a more specific question, or check the tool_calls trace for what happened.",
        trace,
    )
