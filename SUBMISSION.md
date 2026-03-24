# Submission Checklist

## Required Links

- [ ] Working demo link (no auth required): `TODO`
- [ ] Public GitHub repository: `TODO`

## Required Artifacts

- [x] README with architecture decisions, storage/database choices, prompting strategy, and guardrails.
- [x] AI coding session logs/transcripts.
- [x] Simple, usable UI.
- [x] No authentication required.

## Functional Requirement Coverage

- [x] Graph construction from business entities and relationships.
- [x] Graph visualization with node exploration.
- [x] Conversational query interface.
- [x] Required example query classes.
- [x] Guardrails for off-topic requests.

## Evaluation-Criteria Mapping

1. **Code quality and architecture**
   - Clear backend/frontend separation.
   - Typed API schemas and dedicated modules by concern.
2. **Graph modelling**
   - Canonical node/edge schema with deterministic IDs.
3. **Database/storage choice**
   - In-memory graph (`NetworkX`) + analytical joins (`DuckDB`) for deterministic answers.
4. **LLM integration and prompting**
   - Structured query planning layer (`query_planner`) from NL query to executable intent.
5. **Guardrails**
   - Domain scope checks and off-topic prompt rejection path.

## Pre-Submission Verification Steps

1. Start backend and frontend.
2. Open UI and verify graph renders.
3. Run sample queries from `/examples`.
4. Verify an off-topic prompt is rejected.
5. Confirm links in `SESSION_LOGS.md` are accessible.
6. Zip logs:

```bash
zip -r ai-session-logs.zip logs/ai-sessions logs/iterations SESSION_LOGS.md
```

## Optional Bonus Items to Extend (If Time)

- [ ] Streaming query responses
- [ ] Semantic/hybrid entity search
- [ ] Highlight graph nodes referenced by answer evidence
- [ ] Conversation memory across turns
