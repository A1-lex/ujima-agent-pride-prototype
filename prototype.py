from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from dotenv import load_dotenv

load_dotenv()

USE_CREWAI = os.getenv("USE_CREWAI", "false").strip().lower() == "true"
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

BASE_DIR = Path(__file__).parent
CASES_DIR = BASE_DIR / "data" / "cases"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

DISTRESS_KEYWORDS = [
    "loan shark",
    "debt collector",
    "no money for school fees",
    "school fees",
    "harassing me",
    "pressure",
]

DISALLOWED_DENIAL_WORDS = ["unreliable", "risky person", "bad borrower"]


@dataclass
class PrototypeResult:
    member_name: str
    route: Literal["scout_only", "guardian_tier1", "hunter_escalation"]
    risk_flags: List[str]
    scout_output: Optional[str]
    guardian_output: Optional[str]
    hunter_output: Optional[str]
    human_review_required: bool


def load_case(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def contains_distress_signal(message: str) -> bool:
    text = message.lower()
    return any(keyword in text for keyword in DISTRESS_KEYWORDS)


def compute_risk_flags(case: Dict[str, Any]) -> List[str]:
    flags: List[str] = []

    if case.get("amount_kes", 0) > 15000:
        flags.append("amount_above_guardian_limit")

    if case.get("children_under_5", 0) >= 2:
        flags.append("young_children_welfare_sensitivity")

    if str(case.get("income_variance", "")).lower() == "high":
        flags.append("high_income_variance")

    if contains_distress_signal(case.get("message", "")):
        flags.append("distress_signal_detected")

    if str(case.get("repayment_history", "")).lower() == "mixed":
        flags.append("repayment_history_mixed")

    return flags


def route_case(case: Dict[str, Any], risk_flags: List[str]) -> str:
    if contains_distress_signal(case.get("message", "")):
        return "hunter_escalation"

    if case.get("amount_kes", 0) <= 15000 and len(risk_flags) < 3:
        return "guardian_tier1"

    return "hunter_escalation"


def dignity_filter(text: str) -> str:
    clean = text
    for word in DISALLOWED_DENIAL_WORDS:
        clean = clean.replace(word, "needs review")
        clean = clean.replace(word.capitalize(), "Needs review")
    return clean


def scout_template(case: Dict[str, Any]) -> str:
    return dignity_filter(
        f"Habari {case['member_name']}, tunaona unahitaji msaada wa kifedha kwa njia isiyoleta stress. "
        f"Tafadhali usikimbilie mkopeshaji wa mtaani; tunaweza kukuunganisha na afisa wa SACCO kwa review ya haraka. "
        f"Ukikubali, tutatuma kesi yako kwa hatua inayofuata leo."
    )


def guardian_template(case: Dict[str, Any], risk_flags: List[str]) -> str:
    amount = case.get("amount_kes", 0)
    livelihood = case.get("livelihood", "member")
    next_peak = case.get("next_income_peak", "next peak season")

    if amount <= 15000 and len(risk_flags) < 3:
        verdict = "Preliminary Tier-1 recommendation: APPROVE WITH REPAYMENT-TIMING CHECK"
    else:
        verdict = "Preliminary Tier-1 recommendation: ESCALATE"

    return dignity_filter(
        f"{verdict}\n"
        f"- Member livelihood: {livelihood}\n"
        f"- Requested amount: KES {amount}\n"
        f"- Key check: do not score the applicant using occupation label alone\n"
        f"- Next likely income peak: {next_peak}\n"
        f"- Risk flags: {', '.join(risk_flags) if risk_flags else 'none'}\n"
        f"- Suggested next step: align repayment to seasonal cash flow and offer human review if needed"
    )


def hunter_template(case: Dict[str, Any], risk_flags: List[str]) -> str:
    return dignity_filter(
        f"Human Review Briefing Packet\n"
        f"Applicant: {case['member_name']}\n"
        f"County: {case['county']}\n"
        f"Livelihood: {case['livelihood']}\n"
        f"Request: KES {case['amount_kes']} for {case['product_type']}\n"
        f"Household sensitivity: children under 5 = {case['children_under_5']}\n"
        f"Income pattern: {case['transaction_pattern']}\n"
        f"Next income peak: {case['next_income_peak']}\n"
        f"Risk flags: {', '.join(risk_flags) if risk_flags else 'none'}\n"
        f"Officer action: review for timing-based restructuring, welfare sensitivity, and dignity-preserving communication"
    )


def maybe_run_crewai(prompt: str, role: str, goal: str, backstory: str) -> str:
    if not USE_CREWAI:
        raise RuntimeError("USE_CREWAI is false; using template mode.")

    try:
        from crewai import Agent, Crew, Process, Task

        agent = Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            verbose=False,
            allow_delegation=False,
            llm=MODEL_NAME,
        )

        task = Task(
            description=prompt,
            expected_output="A concise, policy-aligned response suitable for SACCO operations.",
            agent=agent,
        )

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
        )

        result = crew.kickoff()
        return dignity_filter(str(result))

    except Exception as e:
        raise RuntimeError(f"CrewAI execution failed: {e}") from e


def run_scout(case: Dict[str, Any]) -> str:
    prompt = (
        "You are the Scout Agent, a financial literacy coach for a Kenyan SACCO. "
        "Write a 3-sentence, warm, non-shaming message for this member. "
        "If there is distress or mention of informal lenders, encourage human review immediately. "
        f"Case data: {json.dumps(case, ensure_ascii=False)}"
    )
    try:
        return maybe_run_crewai(
            prompt=prompt,
            role="Scout Agent",
            goal="Provide supportive literacy guidance and detect distress early.",
            backstory="You coach SACCO members with warmth, never shame them, and never make final credit decisions.",
        )
    except Exception:
        return scout_template(case)


def run_guardian(case: Dict[str, Any], risk_flags: List[str]) -> str:
    prompt = (
        "You are the Guardian Agent, responsible for Tier-1 loan triage only. "
        "Assess the case without using occupation as destiny. "
        "Reference seasonality, household sensitivity, and repayment timing. "
        "If the case is above KES 15,000 or complex, recommend escalation. "
        f"Case data: {json.dumps(case, ensure_ascii=False)} "
        f"Risk flags: {risk_flags}"
    )
    try:
        return maybe_run_crewai(
            prompt=prompt,
            role="Guardian Agent",
            goal="Perform bounded Tier-1 loan triage with fairness and seasonality awareness.",
            backstory="You can recommend only low-risk Tier-1 outcomes and must escalate sensitive cases.",
        )
    except Exception:
        return guardian_template(case, risk_flags)


def run_hunter(case: Dict[str, Any], risk_flags: List[str]) -> str:
    prompt = (
        "You are the Hunter Agent, a human-in-the-loop coordinator. "
        "Do not approve or deny the loan. "
        "Prepare a briefing packet for a human officer, highlighting welfare sensitivity, seasonality, "
        "repayment timing, and fairness risks. "
        f"Case data: {json.dumps(case, ensure_ascii=False)} "
        f"Risk flags: {risk_flags}"
    )
    try:
        return maybe_run_crewai(
            prompt=prompt,
            role="Hunter Agent",
            goal="Prepare high-quality human review briefings for escalated cases.",
            backstory="You coordinate officers, prioritize urgent cases, and preserve human accountability.",
        )
    except Exception:
        return hunter_template(case, risk_flags)


def run_case(case: Dict[str, Any]) -> PrototypeResult:
    if not case.get("consent_status", False):
        return PrototypeResult(
            member_name=case.get("member_name", "Unknown"),
            route="hunter_escalation",
            risk_flags=["consent_missing"],
            scout_output=None,
            guardian_output=None,
            hunter_output="Processing paused: member consent missing. Route to human review and consent clarification.",
            human_review_required=True,
        )

    risk_flags = compute_risk_flags(case)
    route = route_case(case, risk_flags)

    scout_output = None
    guardian_output = None
    hunter_output = None
    human_review_required = False

    if contains_distress_signal(case.get("message", "")):
        scout_output = run_scout(case)

    if route == "guardian_tier1":
        guardian_output = run_guardian(case, risk_flags)
    else:
        guardian_output = run_guardian(case, risk_flags)
        hunter_output = run_hunter(case, risk_flags)
        human_review_required = True

    return PrototypeResult(
        member_name=case["member_name"],
        route=route,
        risk_flags=risk_flags,
        scout_output=scout_output,
        guardian_output=guardian_output,
        hunter_output=hunter_output,
        human_review_required=human_review_required,
    )


def save_result(case_path: Path, result: PrototypeResult) -> None:
    slug = case_path.stem
    json_path = OUTPUT_DIR / f"{slug}_result.json"
    md_path = OUTPUT_DIR / f"{slug}_result.md"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(asdict(result), f, indent=2, ensure_ascii=False)

    markdown = [
        f"# Prototype Result — {result.member_name}",
        "",
        f"- Route: {result.route}",
        f"- Human review required: {result.human_review_required}",
        f"- Risk flags: {', '.join(result.risk_flags) if result.risk_flags else 'none'}",
        "",
    ]

    if result.scout_output:
        markdown.extend(["## Scout Output", result.scout_output, ""])

    if result.guardian_output:
        markdown.extend(["## Guardian Output", result.guardian_output, ""])

    if result.hunter_output:
        markdown.extend(["## Hunter Output", result.hunter_output, ""])

    with md_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(markdown))


def main() -> None:
    case_files = sorted(CASES_DIR.glob("*.json"))
    if not case_files:
        raise FileNotFoundError(f"No JSON files found in {CASES_DIR}")

    for case_path in case_files:
        case = load_case(case_path)
        result = run_case(case)
        save_result(case_path, result)
        print(f"Processed: {case_path.name} -> {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
