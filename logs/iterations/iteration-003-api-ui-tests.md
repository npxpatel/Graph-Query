# Iteration 003 - API, UI, and Tests

- **goal**: deliver graph APIs, chat query endpoint with guardrails, frontend graph+chat UI, and test coverage.
- **prompt(s) used**: implement assignment-required API features and pass tests for example queries and guardrails.
- **debugging steps**:
  - pytest collection failed due to Python 3.9 type-union syntax
  - replaced `| None` annotations with `Optional[...]`
  - API tests initially failed due to startup-state loading in test context
  - added eager/fallback state loading in API
  - trace query initially guardrail-rejected, expanded domain hint vocabulary
- **what changed**:
  - complete FastAPI endpoint set
  - guardrail policy and structured intent responses
  - React graph + chat + node inspector + expand behavior
  - backend tests (7 passing)
  - deployment config files for Render/Vercel
- **before/after result**:
  - before: no integrated end-to-end interface
  - after: working full-stack flow with tested backend behavior
- **next hypothesis**: finalize public deployment URLs and attach raw AI transcript exports for submission bundle.
