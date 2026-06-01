# Ujima Agent Pride Prototype

A lightweight CrewAI-aligned prototype for the fictional Ujima SACCO capstone, now with Flow-first orchestration, Streamlit-based human review, SQLite reviewer history, and member-friendly explanation cards.

## Deployed demo
This repo also includes a Streamlit front end in [app.py](app.py).

Run locally:

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app runs in deterministic template mode by default so it stays stable for deployment.

The deployed demo now uses a Flow-first orchestration layer in [ujima_flow.py](ujima_flow.py) and exposes an execution trace in the UI.

It also stores reviewer decisions in SQLite via [review_store.py](review_store.py) and renders plain-language explanation cards from [explanations.py](explanations.py).

You can also run the sample evaluator locally:

```bash
python evaluate_flow.py
```

## Human-in-the-loop checkpoint
The deployed demo includes a Streamlit-based human review checkpoint for escalated cases.

What it does:
- cases that require escalation surface a review packet
- a human reviewer can choose:
  - `approve_for_human_queue`
  - `return_for_more_information`
  - `reject_recommendation`
- the workflow trace and audit notes are updated in the UI
- reviewer decisions are saved locally in `data/review_history.db`
- the results area includes member-friendly explanation cards for the risk flags that were detected

Why this matters:
This demonstrates the PRIDE-style pause point from the capstone, even when the app is running in a public web demo environment.

The top status row now uses custom stat cards so long values do not get cut off in narrow columns.

To enable live CrewAI/OpenAI outputs on Streamlit Community Cloud, add these secrets in the app settings:

```toml
OPENAI_API_KEY = "your_real_key_here"
MODEL_NAME = "gpt-4o-mini"
USE_CREWAI = true
```

## What this prototype demonstrates
- 3-agent ecosystem:
  - Scout Agent (financial literacy coach)
  - Guardian Agent (Tier-1 loan triage)
  - Hunter Agent (human-in-the-loop coordinator)
- Bounded autonomy
- Human escalation for complex or welfare-sensitive cases
- Dignity-preserving communication
- Simple safety rails and audit-friendly outputs

## Why the prototype is structured this way
This capstone is Kenya-first and SACCO-specific. The prototype keeps:
- raw case handling local
- explicit escalation for sensitive cases
- occupation labels from being treated as destiny
- seasonal-income awareness in the decision path

## Run locally
Use a Python environment of your choice, then run:

```bash
conda activate [your env name]
python prototype.py
```

If you prefer `venv`, activate that environment instead and run the same command.

Outputs will appear in the output/ folder.

For the deployed demo, use:

```bash
streamlit run app.py
```

## Optional CrewAI mode
If you have a working API key and want LLM-generated outputs:

1. Copy .env.example to .env
2. Add your API key
3. Set:

```env
USE_CREWAI=true
```

If USE_CREWAI=false, the prototype still runs in deterministic template mode.

## Sample test cases
- case_1_tier1_market_vendor.json
- case_2_school_fees_escalation.json
- case_3_loan_shark_signal.json

## License
This repository is licensed under the MIT License. See [LICENSE](LICENSE) for the full text.