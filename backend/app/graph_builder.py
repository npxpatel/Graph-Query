from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Set

import networkx as nx
import pandas as pd


@dataclass
class CanonicalData:
    orders: pd.DataFrame
    deliveries: pd.DataFrame
    invoices: pd.DataFrame
    payments: pd.DataFrame
    order_items: pd.DataFrame
    customers: pd.DataFrame
    products: pd.DataFrame
    sql_tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    table_registry: dict[str, list[str]] = field(default_factory=dict)


def node_id(entity_type: str, entity_id: str) -> str:
    return f"{entity_type}:{entity_id}"


def _read_csv(path: Path, required_cols: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=required_cols)
    df = pd.read_csv(path)
    for col in required_cols:
        if col not in df.columns:
            df[col] = None
    return df[required_cols]


def _read_jsonl_parts(folder: Path) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    if not folder.exists():
        return pd.DataFrame()
    for part in sorted(folder.glob("*.jsonl")):
        with part.open("r", encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if not text:
                    continue
                records.append(json.loads(text))
    return pd.DataFrame(records)


def _clean_id_columns(df: pd.DataFrame, id_cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in id_cols:
        if col in out.columns:
            out[col] = out[col].astype(str).str.strip()
            out[col] = out[col].replace({"nan": None, "None": None, "": None})
    return out


def _empty_frame(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def load_data_entity(data_entity_dir: str) -> CanonicalData:
    base = Path(data_entity_dir)
    sales_order_headers = _read_jsonl_parts(base / "sales_order_headers")
    sales_order_items = _read_jsonl_parts(base / "sales_order_items")
    delivery_headers = _read_jsonl_parts(base / "outbound_delivery_headers")
    delivery_items = _read_jsonl_parts(base / "outbound_delivery_items")
    billing_headers = _read_jsonl_parts(base / "billing_document_headers")
    billing_items = _read_jsonl_parts(base / "billing_document_items")
    payments_ar = _read_jsonl_parts(base / "payments_accounts_receivable")
    journal_ar = _read_jsonl_parts(base / "journal_entry_items_accounts_receivable")
    business_partners = _read_jsonl_parts(base / "business_partners")
    products = _read_jsonl_parts(base / "products")
    product_descriptions = _read_jsonl_parts(base / "product_descriptions")

    if sales_order_headers.empty:
        # Fallback for cases where data-entity folder exists but has no records.
        return CanonicalData(
            orders=_empty_frame(["order_id", "customer_id", "order_date", "status"]),
            deliveries=_empty_frame(["delivery_id", "order_id", "plant_id", "delivery_date", "status"]),
            invoices=_empty_frame(["invoice_id", "order_id", "delivery_id", "invoice_date", "status"]),
            payments=_empty_frame(["payment_id", "invoice_id", "payment_date", "amount", "status"]),
            order_items=_empty_frame(["order_item_id", "order_id", "product_id", "quantity", "amount"]),
            customers=_empty_frame(["customer_id", "customer_name", "segment", "region"]),
            products=_empty_frame(["product_id", "product_name", "category"]),
        )

    orders = sales_order_headers.rename(
        columns={
            "salesOrder": "order_id",
            "soldToParty": "customer_id",
            "creationDate": "order_date",
            "overallDeliveryStatus": "status",
            "transactionCurrency": "currency",
            "totalNetAmount": "total_net_amount",
        }
    )
    orders = _clean_id_columns(orders, ["order_id", "customer_id"])

    order_items = sales_order_items.rename(
        columns={
            "salesOrder": "order_id",
            "salesOrderItem": "sales_order_item",
            "material": "product_id",
            "requestedQuantity": "quantity",
            "netAmount": "amount",
        }
    )
    order_items["order_item_id"] = (
        order_items["order_id"].astype(str).fillna("") + "-" + order_items["sales_order_item"].astype(str).fillna("")
    )
    order_items = _clean_id_columns(order_items, ["order_item_id", "order_id", "product_id"])

    deliveries = delivery_items.rename(
        columns={
            "deliveryDocument": "delivery_id",
            "referenceSdDocument": "order_id",
            "plant": "plant_id",
        }
    )
    if not delivery_headers.empty:
        header_cols = ["deliveryDocument", "creationDate", "overallGoodsMovementStatus"]
        header_cols = [c for c in header_cols if c in delivery_headers.columns]
        deliveries = deliveries.merge(
            delivery_headers[header_cols].rename(
                columns={
                    "deliveryDocument": "delivery_id",
                    "creationDate": "delivery_date",
                    "overallGoodsMovementStatus": "status",
                }
            ),
            on="delivery_id",
            how="left",
        )
    deliveries = _clean_id_columns(deliveries, ["delivery_id", "order_id", "plant_id"])
    deliveries = deliveries.drop_duplicates(subset=["delivery_id", "order_id"])

    delivery_to_order = deliveries[["delivery_id", "order_id"]].dropna().drop_duplicates()

    invoices = billing_items.rename(
        columns={
            "billingDocument": "invoice_id",
            "referenceSdDocument": "delivery_id",
            "material": "product_id",
            "netAmount": "amount",
        }
    )
    if not billing_headers.empty:
        billing_header_cols = [
            "billingDocument",
            "billingDocumentDate",
            "billingDocumentIsCancelled",
            "accountingDocument",
            "transactionCurrency",
        ]
        billing_header_cols = [c for c in billing_header_cols if c in billing_headers.columns]
        invoices = invoices.merge(
            billing_headers[billing_header_cols].rename(
                columns={
                    "billingDocument": "invoice_id",
                    "billingDocumentDate": "invoice_date",
                    "billingDocumentIsCancelled": "is_cancelled",
                    "accountingDocument": "accounting_document",
                    "transactionCurrency": "currency",
                }
            ),
            on="invoice_id",
            how="left",
        )
    invoices = invoices.merge(delivery_to_order, on="delivery_id", how="left")
    invoices = _clean_id_columns(invoices, ["invoice_id", "order_id", "delivery_id"])
    invoices["status"] = invoices.get("is_cancelled", False).apply(lambda x: "cancelled" if bool(x) else "billed")
    invoices = invoices.drop_duplicates(subset=["invoice_id", "delivery_id", "order_id"])

    journal_lookup = _empty_frame(["invoice_id", "payment_id"])
    if not journal_ar.empty and "referenceDocument" in journal_ar.columns:
        journal_lookup = journal_ar.rename(columns={"referenceDocument": "invoice_id", "accountingDocument": "payment_id"})
        journal_lookup = journal_lookup[["invoice_id", "payment_id"]].dropna().drop_duplicates()

    payments = payments_ar.rename(
        columns={
            "clearingAccountingDocument": "payment_id",
            "invoiceReference": "invoice_id",
            "postingDate": "payment_date",
            "amountInTransactionCurrency": "amount",
            "financialAccountType": "status",
        }
    )
    payments = _clean_id_columns(payments, ["payment_id", "invoice_id"])
    if "invoice_id" in payments.columns and payments["invoice_id"].isna().all():
        payments = payments.merge(journal_lookup, on="payment_id", how="left")
        if "invoice_id_y" in payments.columns:
            payments["invoice_id"] = payments["invoice_id_y"]
            payments = payments.drop(columns=[c for c in ["invoice_id_x", "invoice_id_y"] if c in payments.columns])
    payments = payments.drop_duplicates(subset=["payment_id", "invoice_id"])

    customers = business_partners.rename(
        columns={
            "customer": "customer_id",
            "businessPartnerName": "customer_name",
            "businessPartnerGrouping": "segment",
            "businessPartnerCategory": "region",
        }
    )
    customers = _clean_id_columns(customers, ["customer_id"])
    customers = customers.drop_duplicates(subset=["customer_id"])

    products_dim = products.rename(
        columns={
            "product": "product_id",
            "productOldId": "product_name",
            "productGroup": "category",
        }
    )
    if not product_descriptions.empty:
        desc = product_descriptions.rename(columns={"product": "product_id", "productDescription": "product_description"})
        desc = desc[["product_id", "product_description"]].drop_duplicates(subset=["product_id"])
        products_dim = products_dim.merge(desc, on="product_id", how="left")
        products_dim["product_name"] = products_dim["product_description"].fillna(products_dim["product_name"])
    products_dim = _clean_id_columns(products_dim, ["product_id"])
    products_dim = products_dim.drop_duplicates(subset=["product_id"])

    sql_tables = {
        "sales_orders": orders,
        "sales_order_items": order_items,
        "deliveries": deliveries,
        "billing_documents": invoices,
        "payments": payments,
        "customers": customers,
        "products": products_dim,
        "flow_links": _build_flow_links(orders, order_items, deliveries, invoices, payments),
    }
    table_registry = {name: sorted(df.columns.tolist()) for name, df in sql_tables.items()}

    return CanonicalData(
        orders=orders,
        deliveries=deliveries,
        invoices=invoices,
        payments=payments,
        order_items=order_items,
        customers=customers,
        products=products_dim,
        sql_tables=sql_tables,
        table_registry=table_registry,
    )


def load_raw_data(raw_dir: str) -> CanonicalData:
    base = Path(raw_dir)
    orders = _read_csv(base / "orders.csv", ["order_id", "customer_id", "order_date", "status"])
    deliveries = _read_csv(base / "deliveries.csv", ["delivery_id", "order_id", "plant_id", "delivery_date", "status"])
    invoices = _read_csv(base / "invoices.csv", ["invoice_id", "order_id", "delivery_id", "invoice_date", "status"])
    payments = _read_csv(base / "payments.csv", ["payment_id", "invoice_id", "payment_date", "amount", "status"])
    order_items = _read_csv(base / "order_items.csv", ["order_item_id", "order_id", "product_id", "quantity", "amount"])
    customers = _read_csv(base / "customers.csv", ["customer_id", "customer_name", "segment", "region"])
    products = _read_csv(base / "products.csv", ["product_id", "product_name", "category"])
    sql_tables = {
        "sales_orders": orders,
        "sales_order_items": order_items,
        "deliveries": deliveries,
        "billing_documents": invoices,
        "payments": payments,
        "customers": customers,
        "products": products,
        "flow_links": _build_flow_links(orders, order_items, deliveries, invoices, payments),
    }
    return CanonicalData(
        orders=orders,
        deliveries=deliveries,
        invoices=invoices,
        payments=payments,
        order_items=order_items,
        customers=customers,
        products=products,
        sql_tables=sql_tables,
        table_registry={name: sorted(df.columns.tolist()) for name, df in sql_tables.items()},
    )


def load_source_data(raw_dir: str, data_entity_dir: str) -> CanonicalData:
    preferred_dirs = [data_entity_dir]
    root = Path(data_entity_dir).resolve().parents[0]
    alt_dirs = [
        str(root / "sap-o2c-data"),
        str(root / "sap-02c-data"),
        str(root / "data-entity"),
    ]
    for d in alt_dirs:
        if d not in preferred_dirs:
            preferred_dirs.append(d)
    for folder in preferred_dirs:
        entity_path = Path(folder)
        if entity_path.exists():
            entity_data = load_data_entity(folder)
            if not entity_data.orders.empty:
                return entity_data
    return load_raw_data(raw_dir)


def normalize_data(data: CanonicalData) -> CanonicalData:
    return CanonicalData(
        orders=_clean_id_columns(data.orders, ["order_id", "customer_id"]),
        deliveries=_clean_id_columns(data.deliveries, ["delivery_id", "order_id", "plant_id"]),
        invoices=_clean_id_columns(data.invoices, ["invoice_id", "order_id", "delivery_id"]),
        payments=_clean_id_columns(data.payments, ["payment_id", "invoice_id"]),
        order_items=_clean_id_columns(data.order_items, ["order_item_id", "order_id", "product_id"]),
        customers=_clean_id_columns(data.customers, ["customer_id"]),
        products=_clean_id_columns(data.products, ["product_id"]),
        sql_tables={k: v.copy() for k, v in data.sql_tables.items()},
        table_registry=data.table_registry.copy(),
    )


def build_graph(data: CanonicalData) -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()

    for _, row in data.customers.iterrows():
        cid = row.get("customer_id")
        if cid:
            g.add_node(node_id("customer", cid), label=row.get("customer_name", cid), entity_type="customer", metadata=row.to_dict())

    for _, row in data.products.iterrows():
        pid = row.get("product_id")
        if pid:
            g.add_node(node_id("product", pid), label=row.get("product_name", pid), entity_type="product", metadata=row.to_dict())

    for _, row in data.orders.iterrows():
        oid = row.get("order_id")
        if not oid:
            continue
        o_node = node_id("order", oid)
        g.add_node(o_node, label=oid, entity_type="order", metadata=row.to_dict())
        customer_id = row.get("customer_id")
        if customer_id:
            c_node = node_id("customer", customer_id)
            if c_node in g.nodes:
                g.add_edge(c_node, o_node, relation="customer_to_order", metadata={})

    for _, row in data.order_items.iterrows():
        item_id = row.get("order_item_id")
        order_id = row.get("order_id")
        product_id = row.get("product_id")
        if not item_id:
            continue
        item_node = node_id("order_item", item_id)
        g.add_node(item_node, label=item_id, entity_type="order_item", metadata=row.to_dict())
        if order_id:
            o_node = node_id("order", order_id)
            if o_node in g.nodes:
                g.add_edge(o_node, item_node, relation="order_to_item", metadata={})
        if product_id:
            p_node = node_id("product", product_id)
            if p_node in g.nodes:
                g.add_edge(item_node, p_node, relation="item_to_product", metadata={})

    for _, row in data.deliveries.iterrows():
        did = row.get("delivery_id")
        oid = row.get("order_id")
        if not did:
            continue
        d_node = node_id("delivery", did)
        g.add_node(d_node, label=did, entity_type="delivery", metadata=row.to_dict())
        if oid:
            o_node = node_id("order", oid)
            if o_node in g.nodes:
                g.add_edge(o_node, d_node, relation="order_to_delivery", metadata={})

    for _, row in data.invoices.iterrows():
        iid = row.get("invoice_id")
        oid = row.get("order_id")
        did = row.get("delivery_id")
        if not iid:
            continue
        i_node = node_id("invoice", iid)
        g.add_node(i_node, label=iid, entity_type="invoice", metadata=row.to_dict())
        if oid:
            o_node = node_id("order", oid)
            if o_node in g.nodes:
                g.add_edge(o_node, i_node, relation="order_to_invoice", metadata={})
        if did:
            d_node = node_id("delivery", did)
            if d_node in g.nodes:
                g.add_edge(d_node, i_node, relation="delivery_to_invoice", metadata={})

    for _, row in data.payments.iterrows():
        pay_id = row.get("payment_id")
        inv_id = row.get("invoice_id")
        if not pay_id:
            continue
        p_node = node_id("payment", pay_id)
        g.add_node(p_node, label=pay_id, entity_type="payment", metadata=row.to_dict())
        if inv_id:
            i_node = node_id("invoice", inv_id)
            if i_node in g.nodes:
                g.add_edge(i_node, p_node, relation="invoice_to_payment", metadata={"amount": row.get("amount")})

    return g


def _build_flow_links(
    orders: pd.DataFrame,
    order_items: pd.DataFrame,
    deliveries: pd.DataFrame,
    invoices: pd.DataFrame,
    payments: pd.DataFrame,
) -> pd.DataFrame:
    if orders.empty:
        return _empty_frame(
            [
                "order_id",
                "delivery_id",
                "invoice_id",
                "payment_id",
                "customer_id",
                "product_id",
            ]
        )
    so = orders[["order_id", "customer_id"]].drop_duplicates()
    oi = (
        order_items[["order_id", "product_id"]].drop_duplicates()
        if not order_items.empty and {"order_id", "product_id"}.issubset(order_items.columns)
        else _empty_frame(["order_id", "product_id"])
    )
    dlv = (
        deliveries[["order_id", "delivery_id"]].drop_duplicates()
        if not deliveries.empty and {"order_id", "delivery_id"}.issubset(deliveries.columns)
        else _empty_frame(["order_id", "delivery_id"])
    )
    inv = (
        invoices[["order_id", "delivery_id", "invoice_id"]].drop_duplicates()
        if not invoices.empty and {"order_id", "delivery_id", "invoice_id"}.issubset(invoices.columns)
        else _empty_frame(["order_id", "delivery_id", "invoice_id"])
    )
    pay = (
        payments[["invoice_id", "payment_id"]].drop_duplicates()
        if not payments.empty and {"invoice_id", "payment_id"}.issubset(payments.columns)
        else _empty_frame(["invoice_id", "payment_id"])
    )

    flow = so.merge(oi, on="order_id", how="left")
    flow = flow.merge(dlv, on="order_id", how="left")
    flow = flow.merge(inv, on=["order_id", "delivery_id"], how="left")
    flow = flow.merge(pay, on="invoice_id", how="left")
    return flow.drop_duplicates()


def graph_to_payload(g: nx.MultiDiGraph, nodes: Optional[Set[str]] = None) -> dict[str, Any]:
    selected = nodes if nodes is not None else set(g.nodes())
    payload_nodes = []
    payload_edges = []
    for n in selected:
        attrs = g.nodes[n]
        payload_nodes.append(
            {
                "id": n,
                "label": attrs.get("label", n),
                "entity_type": attrs.get("entity_type", "unknown"),
                "metadata": attrs.get("metadata", {}),
            }
        )
    for source, target, attrs in g.edges(data=True):
        if source in selected and target in selected:
            payload_edges.append(
                {
                    "source": source,
                    "target": target,
                    "relation": attrs.get("relation", "related_to"),
                    "metadata": attrs.get("metadata", {}),
                }
            )
    return {"nodes": payload_nodes, "edges": payload_edges}


def bfs_subgraph_nodes(g: nx.MultiDiGraph, center_node_id: str, depth: int = 1) -> set[str]:
    if center_node_id not in g.nodes:
        return set()
    visited = {center_node_id}
    frontier = {center_node_id}
    for _ in range(max(depth, 0)):
        next_frontier: set[str] = set()
        for node in frontier:
            next_frontier.update(g.successors(node))
            next_frontier.update(g.predecessors(node))
        next_frontier -= visited
        visited.update(next_frontier)
        frontier = next_frontier
        if not frontier:
            break
    return visited


def graph_integrity_report(g: nx.MultiDiGraph) -> dict[str, Any]:
    entity_counts: dict[str, int] = {}
    for _, attrs in g.nodes(data=True):
        et = attrs.get("entity_type", "unknown")
        entity_counts[et] = entity_counts.get(et, 0) + 1
    relation_counts: dict[str, int] = {}
    for _, _, attrs in g.edges(data=True):
        rel = attrs.get("relation", "related_to")
        relation_counts[rel] = relation_counts.get(rel, 0) + 1
    return {
        "node_count": g.number_of_nodes(),
        "edge_count": g.number_of_edges(),
        "entity_counts": entity_counts,
        "relation_counts": relation_counts,
    }
