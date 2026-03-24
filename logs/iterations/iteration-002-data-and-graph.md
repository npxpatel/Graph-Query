# Iteration 002 - Data and Graph

- **goal**: implement ingestion, normalization, canonical schema, graph construction, and query primitives.
- **prompt(s) used**: build graph-based pipeline with deterministic IDs and support required query intents.
- **debugging steps**:
  - initial normalization script failed (`ModuleNotFoundError: pandas`)
  - created backend virtualenv and installed dependencies
  - reran normalization successfully
- **what changed**:
  - sample raw CSVs for all core entities
  - normalization script and processed exports
  - graph builder and integrity report
  - query planner and query engine
- **before/after result**:
  - before: no ingestable dataset and no graph
  - after: normalized data and executable graph/query core
- **next hypothesis**: wire API endpoints and frontend interactions, then validate using tests for all required examples.
