# BigQuery AI Assistant - Backend

A Flask backend that turns plain-English business questions into BigQuery
insights, using Gemini 2.5 Flash (via Vertex AI) as the agent and Google's
**managed BigQuery Remote MCP Server** for schema discovery + SQL execution.
No LangChain, no LlamaIndex, no CrewAI - only official SDKs, matching your
spec.

## Architecture mapping

| Diagram box | This codebase |
|---|---|
| Chat Interface | (not built yet - test via curl/Postman for now) |
| Flask REST API | `app.py`, `app/routes/chat.py`, `app/routes/health.py` |
| Vertex AI Agent (Gemini 2.5 Flash) | `app/agent/vertex_agent.py` + `app/services/vertex.py` |
| Semantic Layer / Business Context | `app/prompts/semantic_layer.py`, assembled into `app/prompts/system_prompt.py` |
| Native MCP Client | `app/mcp/client.py` (official `mcp` SDK, Streamable HTTP) |
| BigQuery MCP Server | Google's managed server at `https://bigquery.googleapis.com/mcp` (no local install) |
| BigQuery (SQL execution) | Happens **inside** the MCP server when it runs the `execute_sql`-style tool - this backend never talks to BigQuery directly during `/chat` |
| Gemini Business Summary | Final turn of the loop in `app/agent/reasoning.py` |
| JSON Response | Returned by `POST /chat` |

`app/services/bigquery.py` is the one exception: it holds a direct
`google-cloud-bigquery` client used **only** by `/health`, as an independent
sanity check that your credentials work - it is never called from `/chat`.

## What's actually implemented right now

Phases 1-6 and most of 9-11 from your plan:
- Project structure, config, logging ✅
- Vertex AI client (`services/vertex.py`) ✅
- BigQuery health check (`services/bigquery.py`) ✅
- Native MCP client wired to the real Google-managed BigQuery MCP server ✅
- System prompt + editable semantic layer ✅
- Manual Gemini tool-calling loop against live MCP tool schemas ✅
- `POST /chat` and `GET /health` ✅

**Not yet implemented** (next things to build, in order):
- Phase 7: conversation memory (right now every `/chat` call is single-turn -
  no `session_id`, no follow-up context). Tell me when you want this and
  I'll add it - it's a relatively small change (store `contents` per
  session, probably in-memory or Redis).
- Phase 8: Dockerizing + Cloud Run deployment.

## One-time GCP setup checklist

1. `PROJECT_ID` has billing enabled and the **BigQuery API** enabled.
2. Your user or service account has, at minimum:
   - `roles/bigquery.user` (to run query jobs)
   - `roles/bigquery.dataViewer` on the dataset(s) you want the agent to read
3. Auth - pick one:
   - **Local/dev:** `gcloud auth application-default login`
   - **Service account:** download a key JSON into `credentials/` and set
     `GOOGLE_APPLICATION_CREDENTIALS` in `.env` to point at it
4. The BigQuery MCP server is OAuth-only (no API keys). If you hit a 401/403
   the first time you call `/chat` or `/health`, check the official current
   setup steps here, since exact requirements can change:
   https://docs.cloud.google.com/bigquery/docs/use-bigquery-mcp

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then fill in PROJECT_ID at minimum
```

Edit `app/prompts/semantic_layer.py` - replace the placeholder
`DATASET_NOTES` and `BUSINESS_GLOSSARY` with your real tables, columns, and
the business vocabulary your users will actually type (e.g. "revenue" ->
`orders.revenue`). This is the single most important file to get right;
everything else is plumbing.

## Run

```bash
python app.py
```

## Test

```bash
curl http://localhost:5000/health
```

```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Which region brought in the most revenue last quarter?"}'
```

Expected `/chat` response shape:

```json
{
  "answer": "Plain-English business insight, grounded in the actual query result.",
  "sql": "SELECT ... (best-effort extraction of the SQL the agent ran)",
  "execution_time_sec": 2.1,
  "tool_calls": [
    {"tool": "list_dataset_ids", "args": {}, "elapsed_sec": 0.3, "error": null, "result_preview": "..."},
    {"tool": "...", "args": {...}, "elapsed_sec": ..., "error": null, "result_preview": "..."}
  ]
}
```

`tool_calls` is there so you can see exactly what the agent did at each
step - this is your Phase 12 logging requirement, surfaced in the API
response as well as written to `logs/application.log`.

## Notes / things worth knowing

- The exact tool names/parameters the BigQuery MCP server exposes are
  **discovered live** at the start of every `/chat` call
  (`mcp_client.list_tools()`) rather than hardcoded - this means the code
  keeps working even if Google changes the server's tool set, but it also
  means the agent spends its first tool call (or two) inspecting schema
  before writing SQL, which is correct behavior, not a bug.
- Each `/chat` request opens a fresh MCP session. That's simpler and safer
  for a backend handling concurrent users than sharing one long-lived
  session, at the cost of a small connection overhead per request - fine
  for this phase.
- Flask is sync; the agent loop is async (the `mcp` SDK and the parts of
  `google-genai` we use are async-first). Each route bridges with
  `asyncio.run(...)`, which is correct for the Flask dev server and for
  gunicorn's default sync workers (one request per worker at a time). If
  you outgrow that, the next step is `gunicorn -k gevent` or moving to an
  ASGI framework - not needed yet.

## Next steps toward your remaining phases

- **Phase 7 (memory):** add a `session_id` to `/chat`, keep a
  `dict[session_id, list[types.Content]]` (swap to Redis for production),
  and pass the existing `contents` into `run_agent_loop` instead of
  starting fresh each time.
- **Phase 8 (deployment):** a `Dockerfile` + `gunicorn app:app` entrypoint,
  deployed to Cloud Run with the service account attached directly to the
  Cloud Run service (no key file needed at all in that case - Cloud Run's
  built-in identity satisfies `google.auth.default()` automatically).

Tell me which one you want next and I'll build it.
