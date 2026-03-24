from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_required_example_query_top_products() -> None:
    class PlannerMock:
        def generate_json_plan(self, prompt: str) -> dict:
            return {
                "decision": "supported",
                "sql_query": "select product_id, count(distinct invoice_id) as billing_documents from flow_links group by product_id order by billing_documents desc limit 5",
                "unsupported_message": "",
                "confidence": 0.9,
                "reasoning_summary": "mocked sql planner",
            }

    app.dependency_overrides = {}
    query = "Which products are associated with the highest number of billing documents?"
    from app import query_planner

    original = query_planner.get_planner_client
    query_planner.get_planner_client = lambda: PlannerMock()
    res = client.post("/query", json={"query": query})
    query_planner.get_planner_client = original
    assert res.status_code == 200
    body = res.json()
    assert body["intent"] == "sql_query"
    assert body["guardrail"] == "passed"
    assert "rows" in body["evidence"]


def test_required_example_query_trace_flow_like_sql() -> None:
    class PlannerMock:
        def generate_json_plan(self, prompt: str) -> dict:
            return {
                "decision": "supported",
                "sql_query": "select order_id, delivery_id, invoice_id, payment_id from flow_links where order_id = '740506' limit 50",
                "unsupported_message": "",
                "confidence": 0.95,
                "reasoning_summary": "mocked flow sql planner",
            }

    query = "Trace the full flow of SO10001"
    from app import query_planner

    original = query_planner.get_planner_client
    query_planner.get_planner_client = lambda: PlannerMock()
    res = client.post("/query", json={"query": query})
    query_planner.get_planner_client = original
    assert res.status_code == 200
    body = res.json()
    assert body["intent"] == "sql_query"
    assert body["guardrail"] == "passed"
    assert "rows" in body["evidence"]


def test_required_example_query_broken_flows_sql() -> None:
    class PlannerMock:
        def generate_json_plan(self, prompt: str) -> dict:
            return {
                "decision": "supported",
                "sql_query": "select order_id, delivery_id, invoice_id from flow_links where (delivery_id is not null and invoice_id is null) or (delivery_id is null and invoice_id is not null) limit 50",
                "unsupported_message": "",
                "confidence": 0.88,
                "reasoning_summary": "mocked anomaly sql planner",
            }

    query = "Identify sales orders that have broken or incomplete flows."
    from app import query_planner

    original = query_planner.get_planner_client
    query_planner.get_planner_client = lambda: PlannerMock()
    res = client.post("/query", json={"query": query})
    query_planner.get_planner_client = original
    assert res.status_code == 200
    body = res.json()
    assert body["intent"] == "sql_query"
    assert "rows" in body["evidence"]


def test_llm_rejects_offtopic() -> None:
    class PlannerMock:
        def generate_json_plan(self, prompt: str) -> dict:
            return {
                "decision": "unsupported",
                "sql_query": "",
                "unsupported_message": "This system is designed to answer questions related to the provided dataset only.",
                "confidence": 0.1,
                "reasoning_summary": "off topic",
            }

    query = "Write me a poem about the moon"
    from app import query_planner

    original = query_planner.get_planner_client
    query_planner.get_planner_client = lambda: PlannerMock()
    res = client.post("/query", json={"query": query})
    query_planner.get_planner_client = original
    assert res.status_code == 200
    body = res.json()
    assert body["guardrail"] == "rejected"
    assert "provided dataset only" in body["answer"]
