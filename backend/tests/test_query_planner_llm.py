from __future__ import annotations

from app.query_planner import plan_query


class MockPlannerClient:
    def __init__(self, payload: dict):
        self.payload = payload

    def generate_json_plan(self, prompt: str) -> dict:
        return self.payload


def test_planner_parses_valid_json_plan() -> None:
    registry = {
        "sales_orders": ["order_id", "customer_id"],
        "flow_links": ["order_id", "invoice_id", "product_id"],
    }
    payload = {
        "decision": "supported",
        "sql_query": "select product_id, count(distinct invoice_id) as billing_documents from flow_links group by product_id",
        "unsupported_message": "",
        "confidence": 0.91,
        "reasoning_summary": "Valid mocked output",
    }
    plan = plan_query("top products by billing docs", registry, planner_client=MockPlannerClient(payload))
    assert plan.decision == "supported"
    assert "select" in plan.sql_query.lower()


def test_planner_marks_unsupported_when_provided() -> None:
    class BadPlannerClient:
        def generate_json_plan(self, prompt: str) -> dict:
            return {
                "decision": "unsupported",
                "sql_query": "",
                "unsupported_message": "This system is designed to answer questions related to the provided dataset only.",
                "confidence": 0.2,
                "reasoning_summary": "Out of domain",
            }

    registry = {"sales_orders": ["order_id"]}
    plan = plan_query("Trace flow of 12345", registry, planner_client=BadPlannerClient())
    assert plan.decision == "unsupported"
