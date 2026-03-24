# Graph-Based Data Modeling and Query System

This project builds a context graph across order-to-cash entities and provides a natural-language query interface with guardrails.

## What is Implemented

- Graph construction from assignment `sap-o2c-data` JSONL shards (`sales_order_*`, `outbound_delivery_*`, `billing_document_*`, `payments_accounts_receivable`, plus supporting entities).
- Interactive graph UI with:
  - node visualization
  - click-to-expand subgraph
  - node metadata inspection
- Conversational query API:
  - natural language input
  - structured-intent planning
  - deterministic graph/SQL-backed execution
  - grounded responses with evidence
- Guardrails to reject off-topic prompts.

## Architecture

- **Backend**: FastAPI + NetworkX + DuckDB + Pandas
- **Frontend**: React + Vite + react-force-graph-2d
- **Data model**: canonical node/edge schema in `data/processed/CANONICAL_SCHEMA.md` with SQL table registry for LLM planning.

High-level flow:

1. Load and normalize `sap-o2c-data/*/*.jsonl` into canonical tables (CSV fallback remains for fixture tests).
2. Build a graph with deterministic node IDs (`entity_type:entity_id`).
3. Accept user query through `/query`.
4. Apply guardrails (domain-only).
5. Use Gemini (or fallback stub) to convert query text into a strict JSON query plan.
6. Execute against graph and/or tabular joins.
7. Return grounded answer + evidence payload.

## Project Structure

- `backend/app/main.py` API and orchestration
- `backend/app/graph_builder.py` ingestion, normalization, graph build, subgraph extraction
- `backend/app/query_planner.py` LLM-driven JSON query planning
- `backend/app/llm_client.py` Gemini provider adapter
- `backend/app/prompts/schema_dictionary.json` schema context passed to planner
- `backend/app/prompts/guardrail_policy.md` guardrail rules passed to planner
- `backend/tests/` API and graph tests
- `frontend/src/App.jsx` graph + chat UI
- `data/raw/` input CSVs
- `data/processed/` normalized outputs and schema docs
- `SESSION_LOGS.md` rubric-mapped AI session log index
- `SUBMISSION.md` final delivery checklist

## Local Run

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Run **backend** and **frontend** in separate terminals (or use your own process manager).

## API Endpoints

- `GET /health`
- `GET /examples`
- `POST /reload`
- `GET /graph/full`
- `GET /graph/integrity`
- `GET /graph/subgraph?center_node_id=<id>&depth=1`
- `GET /node/{node_id}`
- `POST /query`

## Required Example Queries

The implementation supports these classes directly:

1. Products with highest billing-document associations.
2. Trace full flow of a billing/sales document.
3. Find broken/incomplete flows (e.g. delivered not billed, billed without delivery).

## Guardrails

The system only answers questions related to the provided order-to-cash dataset.

Off-topic requests (for example creative writing or general knowledge prompts) return:

> This system is designed to answer questions related to the provided dataset only.

## Testing

```bash
cd backend
source .venv/bin/activate
pytest -q
```

Current status: backend tests pass for graph integrity, required query categories, and guardrail rejection.

## Deployment (Free Tier)

Suggested split:

- **Backend**: Render (free web service) via `render.yaml` + `backend/Dockerfile`
- **Frontend**: Vercel (free static hosting) via `frontend/vercel.json`

Set frontend environment variable:

- `VITE_API_BASE=https://<your-render-backend-url>`

Set backend environment variable:

- `CORS_ORIGINS=https://<your-vercel-frontend-url>`

## LLM Strategy and Tradeoffs

- NL query translation uses the Gemini HTTP API (`LLM_PROVIDER=gemini`) with strict JSON response requirements.
- Set `LLM_MODEL` in `.env` to any model id your key can call with `generateContent` (Google retires and renames models; list available ids with `GET https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_KEY`). The app does not whitelist model names.
- Planner outputs either:
  - `supported` + executable `sql_query`, or
  - `unsupported` + dataset-domain rejection message.
- Backend executes only safe single-statement `SELECT` SQL against registered dataset tables.
- If API key is missing, query planning fails with an explicit planner error response.

