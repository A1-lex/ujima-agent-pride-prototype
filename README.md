# Ujima Agent Pride Prototype

A lightweight CrewAI-aligned prototype for the fictional Ujima SACCO capstone.

## Deployed demo
This repo also includes a Streamlit front end in [app.py](app.py).

Run locally:

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app runs in deterministic template mode by default so it stays stable for deployment.

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