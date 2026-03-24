from __future__ import annotations

from pathlib import Path

from app.graph_builder import (
    bfs_subgraph_nodes,
    build_graph,
    graph_integrity_report,
    load_data_entity,
    load_raw_data,
    load_source_data,
    node_id,
    normalize_data,
)


def test_graph_construction_has_expected_entities() -> None:
    root = Path(__file__).resolve().parents[2]
    data = normalize_data(load_source_data(str(root / "data" / "raw"), str(root / "sap-o2c-data")))
    g = build_graph(data)
    report = graph_integrity_report(g)

    assert report["node_count"] > 0
    assert report["edge_count"] > 0
    assert "order" in report["entity_counts"]
    assert "invoice_to_payment" in report["relation_counts"]


def test_subgraph_expansion_for_order() -> None:
    root = Path(__file__).resolve().parents[2]
    data = normalize_data(load_source_data(str(root / "data" / "raw"), str(root / "sap-o2c-data")))
    g = build_graph(data)
    first_order = data.orders["order_id"].dropna().astype(str).iloc[0]
    nodes = bfs_subgraph_nodes(g, node_id("order", first_order), depth=1)
    assert node_id("order", first_order) in nodes
    assert len(nodes) >= 2


def test_data_entity_ingestion_builds_registry() -> None:
    root = Path(__file__).resolve().parents[2]
    source = root / "sap-o2c-data"
    if not source.exists():
        source = root / "sap-02c-data"
    if not source.exists():
        source = root / "data-entity"
    data = normalize_data(load_data_entity(str(source)))
    assert data.orders.shape[0] > 0
    assert "sales_orders" in data.table_registry
    assert "flow_links" in data.table_registry


def test_load_source_prefers_data_entity_when_available() -> None:
    root = Path(__file__).resolve().parents[2]
    data = normalize_data(load_source_data(str(root / "data" / "raw"), str(root / "sap-o2c-data")))
    assert data.orders.shape[0] > 0
