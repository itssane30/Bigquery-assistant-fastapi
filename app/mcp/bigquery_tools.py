"""
app/mcp/bigquery_tools.py
----------------------------
Converts BigQuery MCP server tool definitions (discovered live via
list_tools()) into the function-declaration format the Gemini API expects.

We deliberately do NOT hardcode tool names or parameter names here. As of
writing, Google's BigQuery Remote MCP server advertises tools along these
lines: list_dataset_ids, get_dataset_info, list_table_ids, get_table_info,
execute_sql - but Google can add/rename tools over time, and a self-hosted
MCP Toolbox server exposes a different (larger) set. Pulling the schema
live keeps this code correct regardless of which MCP server is configured.
"""

from typing import Any


def mcp_tools_to_gemini_declarations(mcp_tools: list) -> list[dict[str, Any]]:
    """Builds Gemini `function_declarations` entries from MCP Tool objects."""
    declarations: list[dict[str, Any]] = []

    for tool in mcp_tools:
        schema = dict(tool.inputSchema) if tool.inputSchema else {"type": "object", "properties": {}}

        # Gemini's function-declaration schema doesn't recognize every
        # JSON-Schema keyword some MCP servers include - strip the ones
        # known to cause validation errors.
        schema.pop("$schema", None)
        schema.pop("additionalProperties", None)
        schema.setdefault("type", "object")
        schema.setdefault("properties", {})

        declarations.append(
            {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": schema,
            }
        )

    return declarations
