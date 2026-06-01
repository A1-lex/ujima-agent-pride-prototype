from pathlib import Path

from prototype import load_case
from ujima_flow import run_case_with_flow


CASES_DIR = Path(__file__).parent / "data" / "cases"


def main():
    for case_file in sorted(CASES_DIR.glob("*.json")):
        case = load_case(case_file)
        result, flow_state = run_case_with_flow(case)
        print("=" * 80)
        print(case_file.name)
        print(f"Route: {result.route}")
        print(f"Human review required: {result.human_review_required}")
        print(f"Risk flags: {result.risk_flags}")
        print(f"Trace steps: {len(flow_state.get('trace', []))}")
        print(f"Audit notes: {flow_state.get('audit_notes', [])}")


if __name__ == "__main__":
    main()
