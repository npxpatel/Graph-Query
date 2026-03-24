# Iteration 007 — Gemini model id from env (no hardcoded default)

## Goal

Stop baking in a single `LLM_MODEL` default that can 404 when Google renames or retires models; treat the model id as fully user-controlled and document how to pick a valid one.

## Symptom

Planner failed with Gemini `404 NOT_FOUND`: `models/gemini-1.5-flash` not found for `v1beta` `generateContent`.

## Changes

- **`backend/app/config.py`**: `llm_model` default is empty; callers must set `LLM_MODEL` in `.env`.
- **`backend/app/llm_client.py`**: Clear error if `LLM_MODEL` is unset; 404 responses include a hint to use ListModels; model string is stripped before use in the URL.
- **`.env.example`**: Example `LLM_MODEL=gemini-2.0-flash`, placeholder API key, comment that any ListModels entry with `generateContent` works.
- **`.env`**: Example local value updated to `gemini-2.0-flash` (user should align with ListModels if 404 persists).
- **`README.md`**: Document that model names are not whitelisted in code.

## Debugging steps

- Confirmed URL shape: `.../v1beta/models/{model}:generateContent` — the `{model}` segment must match a current API model `name` suffix.

## Before / after

- **Before**: Default `gemini-1.5-flash` could 404 when no longer published for the key’s API surface.
- **After**: No default model in code; explicit `LLM_MODEL` plus ListModels hint on 404.

## Next hypothesis

If `gemini-2.0-flash` is unavailable for a given key or region, the user sets `LLM_MODEL` to another id from ListModels without code changes.
