from typing import Any

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    label: str
    entity_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphPayload(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class SubgraphResponse(BaseModel):
    center_node_id: str
    depth: int
    graph: GraphPayload


class NodeResponse(BaseModel):
    node: GraphNode
    neighbors: list[str]


class QueryRequest(BaseModel):
    query: str


class StructuredQuery(BaseModel):
    decision: str = "supported"  # supported | unsupported
    sql_query: str = ""
    unsupported_message: str = ""
    confidence: float = 0.0
    reasoning_summary: str = ""


class QueryResponse(BaseModel):
    query: str
    intent: str
    answer: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    structured_query: StructuredQuery
    guardrail: str = "llm_handled"
