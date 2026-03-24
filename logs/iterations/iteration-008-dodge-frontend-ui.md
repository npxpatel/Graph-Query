# Iteration 008 — Dodge-style Order-to-Cash UI and readable chat

## Goal

Align the React frontend with the provided “Mapping / Order to Cash” reference: light shell, graph + chat split, Dodge AI chat chrome, and stop dumping raw JSON in assistant replies.

## Changes

- **`frontend/src/App.jsx`**: Top nav with breadcrumb, graph toolbar (`Minimize`, `Hide Granular Overlay`, `Reset graph`), light-theme force graph (blue/red nodes, light link strokes), floating node detail card (key/value, readability note) instead of raw JSON inspector, chat header “Chat with Graph” / “Order to Cash”, user dark bubbles, assistant natural-language answer plus optional results table, collapsible “technical details” for SQL/planner notes only (no full JSON blobs).
- **`frontend/src/styles.css`**: New light palette, DM Sans, layout (~flex graph + fixed-width chat), pill controls, compose strip with green status dot and bottom-right Send.
- **`frontend/index.html`**: Title `Mapping / Order to Cash`.

## Debugging / validation

- `npm run build` in `frontend/` succeeds.

## Next hypothesis

If product owners want zero technical disclosure, remove or gate the “Show technical details” toggle behind a dev flag.
