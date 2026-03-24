from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import settings
from app.llm_client import get_planner_client
from app.schemas import StructuredQuery


def plan_query(query: str, table_registry: dict[str, list[str]], planner_client: Any = None) -> StructuredQuery:
    client = planner_client or get_planner_client()
    prompt = _build_prompt(query, table_registry)
    raw_plan = client.generate_json_plan(prompt)
    normalized = _normalize_plan(raw_plan)
    return StructuredQuery(**normalized)


def _build_prompt(query: str, table_registry: dict[str, list[str]]) -> str:
    registry_lines = []
    for table_name, columns in sorted(table_registry.items()):
        shown = ", ".join(columns[:20])
        registry_lines.append(f"- {table_name}: {shown}")
    registry_text = "\n".join(registry_lines)
    schema_context = _load_schema_context(table_registry)
    guardrail_context = _load_guardrail_context()
    return f"""
You are a query translator for an order-to-cash business dataset.
Translate the natural language question into either:
1) a SQL query over allowed tables/columns
2) an unsupported-domain message

Use ONLY the listed tables/columns:
{registry_text}

Schema dictionary (authoritative business semantics):
{schema_context}

Guardrail policy:
{guardrail_context}

Return ONLY JSON object with exact keys:
decision, sql_query, unsupported_message, confidence, reasoning_summary

Rules:
- decision must be either "supported" or "unsupported"
- if decision is "supported":
  - sql_query must be a single SELECT query only
  - no INSERT/UPDATE/DELETE/ALTER/DROP/TRUNCATE/CREATE
  - no semicolons
  - unsupported_message must be empty
- if decision is "unsupported":
  - sql_query must be empty
  - unsupported_message must be exactly:
    "This system is designed to answer questions related to the provided dataset only."

Question:
{query}
""".strip()


def _load_schema_context(table_registry: dict[str, list[str]]) -> str:
    path = Path(settings.schema_dictionary_path)
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            # Keep prompt compact but rich.
            return json.dumps(raw, ensure_ascii=True)
        except json.JSONDecodeError:
            pass
    fallback = {"tables": table_registry, "note": "fallback from runtime table registry"}
    return json.dumps(fallback, ensure_ascii=True)


def _load_guardrail_context() -> str:
    path = Path(settings.guardrail_policy_path)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return (
        "In-domain only: order-to-cash dataset. Reject off-topic queries and keep operations within known schema."
    )


def _normalize_plan(raw_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": raw_plan.get("decision", "unsupported"),
        "sql_query": raw_plan.get("sql_query", ""),
        "unsupported_message": raw_plan.get(
            "unsupported_message", "This system is designed to answer questions related to the provided dataset only."
        ),
        "confidence": raw_plan.get("confidence", 0.0),
        "reasoning_summary": raw_plan.get("reasoning_summary", ""),
    }
