# Graph-Based Data Modeling and Query System

This project builds a context graph across order-to-cash entities and provides a natural-language query interface with guardrails.

## Architecture decisions

- **Split responsibilities**: The **LLM** only proposes a structured plan (JSON); the **backend** validates and executes it. Answers are always grounded in loaded data, not in free-form model prose about facts.
- **Backend stack**: **FastAPI** for a small, typed HTTP API; **Pandas** for ingestion and normalization; **NetworkX** for graph storage, traversal, and subgraph APIs; **no separate graph database service**—the graph is in-memory and rebuilt from the same canonical tables used for analytics.
- **Frontend stack**: **React + Vite** for a fast static UI; **react-force-graph-2d** for interactive exploration (pan/zoom, click-to-expand neighborhood).
- **Monorepo layout**: `backend/` and `frontend/` deploy independently (e.g. Render + Vercel); shared contract is HTTP + JSON.

**End-to-end flow**

1. Load and normalize `sap-o2c-data/*/*.jsonl` into canonical tables (CSV under `data/raw/` is a **test/fixture** fallback only).
2. Build a **NetworkX** graph with deterministic node IDs (`entity_type:entity_id`) and typed edges.
3. User sends natural language to **`POST /query`**.
4. **Query planner** (Gemini) returns a strict JSON plan: supported + `sql_query`, or unsupported + fixed domain message.
5. If supported, the server runs **only** validated **`SELECT`** SQL (see Guardrails); results and metadata are returned as structured evidence for the UI.

## Database and storage choice

There is **no standalone database server** (no Postgres/MySQL in production for this assignment).

- **Analytical queries**: **DuckDB** runs **in-process and in-memory**. At request time, canonical tables are **registered** from Pandas DataFrames (`con.register(table_name, df)`), then a single `SELECT` from the planner is executed. This keeps deployment simple (one container, no DB provisioning) and guarantees queries run over the **same** snapshot of data the graph was built from.
- **Graph**: **NetworkX** `MultiDiGraph` in memory—good for BFS/subgraph extraction and integrity checks without serializing to a graph DB.
- **Tradeoff**: Data lives in RAM; scaling to huge datasets would require a different storage layer. For the provided O2C shards, this is a deliberate simplicity vs. operational cost choice.

## LLM prompting strategy

- **Provider**: **Google Gemini** via the Generative Language HTTP API (`generateContent`, JSON response mode). Model id is configured with **`LLM_MODEL`** (not hardcoded to a single model name).
- **Prompt construction** (`backend/app/query_planner.py`):
  - **Runtime table/column registry** is injected so the model only references tables that actually exist.
  - **`schema_dictionary.json`** is embedded as the **authoritative** business semantics (table purposes, keys, relationships).
  - **`guardrail_policy.md`** is included verbatim so refusal style and domain scope are explicit in the prompt.
- **Output contract**: The model must return **only** JSON with keys `decision`, `sql_query`, `unsupported_message`, `confidence`, `reasoning_summary`. Supported plans must be a **single** `SELECT` with no semicolons and no mutating SQL.
- **Failure modes**: Malformed JSON or planner errors surface as a controlled API response (not silent fallback to guessed SQL).

## Guardrails

1. **Domain / intent**: The planner is instructed to mark **`unsupported`** for off-topic or non-dataset questions and to use the **exact** canned message:  
   *"This system is designed to answer questions related to the provided dataset only."* (enforced in code when parsing the plan.)
2. **SQL safety** (before execution): Only statements that pass checks—must start with `SELECT`, no `INSERT`/`UPDATE`/`DELETE`/DDL, no multiple statements—are run (`main.py`).
3. **No arbitrary execution**: The LLM never gets raw shell or arbitrary Python; it only proposes SQL over the registered schema.
4. **CORS**: Configurable **`CORS_ORIGINS`** so only trusted frontends call the API in deployed environments.

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
- Guardrails to reject off-topic prompts (see above).

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

## Testing

```bash
cd backend
source .venv/bin/activate
pytest -q
```

Current status: backend tests pass for graph integrity, required query categories, and guardrail rejection.

## Deployment (Free Tier)

Suggested split:

- **Backend**: Render (native Python with **Root Directory** `backend`, or Docker via `render.yaml`)
- **Frontend**: Vercel (static + SPA rewrites) — `frontend/vercel.json`

### Backend (Render) quick reminder

`requirements.txt` is under **`backend/`**. Either set Render **Root Directory** to `backend` and use `pip install -r requirements.txt`, or leave root empty and use `pip install -r backend/requirements.txt`. **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

### Frontend (Vercel)

1. Go to [vercel.com](https://vercel.com) → **Add New** → **Project** → import the same GitHub repo.
2. **Configure Project**
   - **Root Directory**: click **Edit** → set to **`frontend`** (monorepo). Vercel should detect **Vite**.
   - **Framework Preset**: Vite (auto if `package.json` has `vite` build).
   - **Build Command**: `npm run build` (default).
   - **Output Directory**: `dist` (Vite default).
3. **Environment Variables** (project → Settings → Environment Variables)  
   Add for **Production** (and **Preview** if you use PR previews):

   | Name | Value |
   |------|--------|
   | `VITE_API_BASE` | `https://your-service.onrender.com` — your **Render** URL **with no trailing slash** |

   Vite bakes this in at **build** time; after changing it, trigger **Redeploy**.
4. **Deploy**. Your site will be `https://<project>.vercel.app` (or a custom domain).
5. **CORS**: On Render, set **`CORS_ORIGINS`** to your Vercel URL (e.g. `https://graph-query-xxx.vercel.app`). Use a comma-separated list if you have preview URLs too.

`frontend/vercel.json` already sends all paths to `/` so client-side routes load the SPA.

## Configuration (LLM and environment)

See **LLM prompting strategy** and **Guardrails** above. For local and hosted runs, set:

| Variable | Purpose |
|----------|---------|
| `LLM_API_KEY` | Gemini API key |
| `LLM_MODEL` | Model id for `generateContent` (list models: `GET https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_KEY`) |
| `LLM_PROVIDER` | `gemini` (default) |
| `CORS_ORIGINS` | Comma-separated frontend origins in production |

If `LLM_API_KEY` or `LLM_MODEL` is missing, the planner returns an explicit error response instead of guessing SQL.

