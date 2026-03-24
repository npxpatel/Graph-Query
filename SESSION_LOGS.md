# AI Session Logs Index

This index maps AI session activity to the evaluation signals requested in the assignment.

## Session Artifact Locations

- Raw exports folder: `logs/ai-sessions/`
- Iteration notes folder: `logs/iterations/`
- Submission bundle target: `ai-session-logs.zip`

## Rubric Mapping

### Prompt quality

- See iteration notes sections: `goal`, `prompt(s) used`, and `next hypothesis`.
- Capture prompt refinements and why wording changed.

### Debugging workflow

- See iteration notes sections: `debugging steps`, `before/after result`.
- Include failing command/test output and final fix.

### Iteration patterns

- Sequence of iteration notes demonstrates the build-test-fix loop and decision changes.

## Current Iterations

- `logs/iterations/iteration-001-foundation.md`
- `logs/iterations/iteration-002-data-and-graph.md`
- `logs/iterations/iteration-003-api-ui-tests.md`
- `logs/iterations/iteration-004-llm-query-upgrade.md`
- `logs/iterations/iteration-005-schema-policy-context.md`
- `logs/iterations/iteration-006-llm-sql-direct-flow.md`
- `logs/iterations/iteration-007-gemini-model-env.md`
- `logs/iterations/iteration-008-dodge-frontend-ui.md`

## How To Add Raw Transcript Exports

1. Export transcript(s) from your AI coding tool.
2. Place raw files under `logs/ai-sessions/` unchanged.
3. Add one line per file below:

| Timestamp | Tool | File | Focus |
|---|---|---|---|
| TODO | Cursor | TODO | TODO |

## LLM Migration Audit Pointers

- **Prompt quality**: see `iteration-004-llm-query-upgrade.md` (`prompt(s) used`) for JSON-contract prompt refinements.
- **Debugging workflow**: same file documents malformed-plan handling, guardrail rejections, and compiler fixes.
- **Iteration patterns**: progression from deterministic intent routing to guarded LLM planning is captured across iterations 002 -> 003 -> 004.
- **Latest alignment**: see `iteration-005-schema-policy-context.md` for schema/policy-file prompt context and dataset-path normalization changes.
- **Direct SQL flow update**: see `iteration-006-llm-sql-direct-flow.md` for SQL-return planner contract and simplified execution path.
- **Gemini model id**: see `iteration-007-gemini-model-env.md` for removing a brittle default model name and documenting ListModels-based configuration.
- **Frontend UX**: see `iteration-008-dodge-frontend-ui.md` for Dodge-style shell, readable chat answers, and graph controls.

## Notes

- Keep raw logs immutable.
- Add only supplemental annotations in iteration notes.
