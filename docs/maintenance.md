# Maintenance Notes

This demo is intentionally split into a stable fallback path and a live CrewAI/OpenAI path so it can be deployed safely on Streamlit Community Cloud.

## Live CrewAI/OpenAI mode
To enable live model behavior on Streamlit Community Cloud, add these secrets in the app settings:

```toml
OPENAI_API_KEY = "your_real_key_here"
MODEL_NAME = "gpt-4o-mini"
USE_CREWAI = true
```

What these settings do:
- `OPENAI_API_KEY` enables OpenAI-backed agent calls.
- `MODEL_NAME` lets you choose which model the live agent path should use.
- `USE_CREWAI = true` turns on the live CrewAI path instead of the deterministic fallback.

## Why the fallback exists
The fallback path is kept on purpose for reliability.

Reasons:
- Streamlit Cloud environments can differ from local dev environments.
- CrewAI or its dependency chain may not import cleanly in every hosted runtime.
- A deterministic fallback keeps the demo usable even when external model calls fail or secrets are missing.
- The public demo should always render, even if live inference is unavailable.

## Fallback behavior
When live mode is unavailable, the app still:
- loads the sample case
- runs the Flow-first orchestration
- produces a deterministic route and trace
- allows human-in-the-loop review for escalated cases
- saves reviewer decisions locally in SQLite
- shows member-friendly explanation cards

## What you can safely change
These are the main extension points:
- prompt wording in the agent helpers
- risk-flag rules in `prototype.py`
- explanation text in `explanations.py`
- reviewer-history storage fields in `review_store.py`
- UI copy in `app.py`

## What to avoid changing casually
These parts are tightly coupled to the demo stability story:
- the import guards around the CrewAI flow runtime
- the deterministic fallback path
- the session-state checkpoint handling
- the SQLite database path under `data/review_history.db`

## Local storage
Reviewer history is stored in `data/review_history.db`.
The app also exposes JSON export from the UI for easy review and backup.
