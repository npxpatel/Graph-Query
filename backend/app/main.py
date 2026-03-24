from __future__ import annotations

from pathlib import Path

import duckdb
import networkx as nx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.graph_builder import (
    bfs_subgraph_nodes,
    build_graph,
    graph_integrity_report,
    graph_to_payload,
    load_source_data,
    normalize_data,
)
from app.llm_client import LLMClientError
from app.query_planner import plan_query
from app.schemas import NodeResponse, QueryRequest, QueryResponse, SubgraphResponse

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_graph: nx.MultiDiGraph = nx.MultiDiGraph()
_data = None


def _load_state() -> None:
    global _graph, _data
    raw_dir = str(Path(settings.data_dir) / "raw")
    _data = normalize_data(load_source_data(raw_dir, settings.data_entity_dir))
    _graph = build_graph(_data)


_load_state()


@app.on_event("startup")
def on_startup() -> None:
    _load_state()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


@app.get("/examples")
def examples() -> dict[str, list[str]]:
    return {
        "examples": [
            "Which products are associated with the highest number of billing documents?",
            "Hey, bro what's up? What's the weather in Tokyo?",
            "Identify sales orders with broken or incomplete flows",
        ]
    }


@app.post("/reload")
def reload_data() -> dict[str, int]:
    _load_state()
    return {"nodes": _graph.number_of_nodes(), "edges": _graph.number_of_edges()}


@app.get("/graph/full")
def full_graph() -> dict:
    return graph_to_payload(_graph)


@app.get("/graph/integrity")
def integrity() -> dict:
    return graph_integrity_report(_graph)


@app.get("/graph/subgraph", response_model=SubgraphResponse)
def subgraph(center_node_id: str, depth: int = 1) -> SubgraphResponse:
    if center_node_id not in _graph.nodes:
        raise HTTPException(status_code=404, detail=f"Node not found: {center_node_id}")
    nodes = bfs_subgraph_nodes(_graph, center_node_id, depth=depth)
    payload = graph_to_payload(_graph, nodes)
    return SubgraphResponse(center_node_id=center_node_id, depth=depth, graph=payload)  # type: ignore[arg-type]


@app.get("/node/{node_id}", response_model=NodeResponse)
def get_node(node_id: str) -> NodeResponse:
    if node_id not in _graph.nodes:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")
    attrs = _graph.nodes[node_id]
    neighbors = list(set(_graph.successors(node_id)).union(set(_graph.predecessors(node_id))))
    return NodeResponse(
        node={
            "id": node_id,
            "label": attrs.get("label", node_id),
            "entity_type": attrs.get("entity_type", "unknown"),
            "metadata": attrs.get("metadata", {}),
        },
        neighbors=neighbors,
    )


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    if _data is None or _graph.number_of_nodes() == 0:
        _load_state()
    try:
        sq = plan_query(req.query, _data.table_registry)
    except (LLMClientError, ValueError) as exc:
        return QueryResponse(
            query=req.query,
            intent="planner_error",
            answer=f"Planner could not process this query: {exc}",
            evidence={},
            structured_query={
                "decision": "unsupported",
                "sql_query": "",
                "unsupported_message": "This system is designed to answer questions related to the provided dataset only.",
                "confidence": 0.0,
                "reasoning_summary": "Planner error",
            },
            guardrail="rejected",
        )
    if sq.decision != "supported":
        return QueryResponse(
            query=req.query,
            intent="unsupported",
            answer=sq.unsupported_message
            or "This system is designed to answer questions related to the provided dataset only.",
            evidence={},
            structured_query=sq,
            guardrail="rejected",
        )
    sql = sq.sql_query.strip()
    if not _is_sql_safe(sql):
        return QueryResponse(
            query=req.query,
            intent="unsafe_sql",
            answer="This system is designed to answer questions related to the provided dataset only.",
            evidence={"sql_query": sql},
            structured_query=sq,
            guardrail="rejected",
        )

    try:
        con = duckdb.connect(":memory:")
        for table_name, df in _data.sql_tables.items():
            con.register(table_name, df)
        result_df = con.execute(sql).df()
        rows = result_df.to_dict(orient="records")
        answer = f"Query executed successfully. Returned {len(rows)} row(s)."
        evidence = {"sql_query": sql, "rows": rows[:100], "planner_reasoning": sq.reasoning_summary}
    except Exception as exc:
        return QueryResponse(
            query=req.query,
            intent="sql_error",
            answer=f"Could not execute the generated SQL safely: {exc}",
            evidence={"sql_query": sql},
            structured_query=sq,
            guardrail="rejected",
        )

    return QueryResponse(
        query=req.query,
        intent="sql_query",
        answer=answer,
        evidence=evidence,
        structured_query=sq,
        guardrail="passed",
    )


def _is_sql_safe(sql: str) -> bool:
    if not sql:
        return False
    lowered = sql.lower().strip()
    forbidden = ["insert ", "update ", "delete ", "drop ", "alter ", "truncate ", "create "]
    if any(token in lowered for token in forbidden):
        return False
    if ";" in lowered:
        return False
    if not lowered.startswith("select "):
        return False
    return True
