from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Tuple

CREWAI_FLOW_AVAILABLE = True
CREWAI_FLOW_ERROR: Exception | None = None

try:
    from crewai.flow.flow import Flow, listen, start
except Exception as exc:  # pragma: no cover - runtime/environment dependent
    CREWAI_FLOW_AVAILABLE = False
    CREWAI_FLOW_ERROR = exc

    class Flow:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            self.state = {}

        def kickoff(self):
            raise RuntimeError("CrewAI Flow is unavailable in this runtime.")

    def listen(*args, **kwargs):  # type: ignore[no-redef]
        def decorator(func):
            return func

        return decorator

    def start(*args, **kwargs):  # type: ignore[no-redef]
        def decorator(func):
            return func

        return decorator

from prototype import (
    PrototypeResult,
    compute_risk_flags,
    contains_distress_signal,
    route_case,
    run_case as legacy_run_case,
    run_guardian as guardian_agent_output,
    run_hunter as hunter_agent_output,
    run_scout as scout_agent_output,
)


class UjimaDecisionFlow(Flow):
    def __init__(self, input_case: Dict[str, Any]):
        super().__init__()
        self.input_case = input_case

    def _trace(self, step: str, status: str, details: str) -> None:
        if "trace" not in self.state:
            self.state["trace"] = []
        self.state["trace"].append(
            {
                "step": step,
                "status": status,
                "details": details,
            }
        )

    def _audit(self, note: str) -> None:
        if "audit_notes" not in self.state:
            self.state["audit_notes"] = []
        self.state["audit_notes"].append(note)

    @start()
    def intake(self):
        case = dict(self.input_case)

        self.state["case"] = case
        self.state["trace"] = []
        self.state["audit_notes"] = []
        self.state["risk_flags"] = []
        self.state["route"] = None
        self.state["human_review_required"] = False
        self.state["scout_output"] = None
        self.state["guardian_output"] = None
        self.state["hunter_output"] = None
        self.state["consent_missing"] = not bool(case.get("consent_status", False))
        self.state["human_checkpoint_required"] = False
        self.state["human_checkpoint_status"] = "not_started"
        self.state["human_checkpoint_feedback"] = None
        self.state["review_packet"] = None

        self._trace(
            "intake",
            "completed",
            f"Loaded case for {case.get('member_name', 'Unknown')} in {case.get('county', 'Unknown')}",
        )

        if self.state["consent_missing"]:
            self._audit("Consent missing: processing must pause for human review.")
            self._trace(
                "consent_check",
                "blocked",
                "Member consent not confirmed.",
            )

        return case

    @listen(intake)
    def assess_risk(self, case):
        if self.state.get("consent_missing"):
            return case

        risk_flags = compute_risk_flags(case)
        route = route_case(case, risk_flags)

        self.state["risk_flags"] = risk_flags
        self.state["route"] = route
        self.state["human_review_required"] = route != "guardian_tier1"

        self._trace(
            "risk_assessment",
            "completed",
            f"Route={route}; risk_flags={risk_flags if risk_flags else ['none']}",
        )

        if "distress_signal_detected" in risk_flags:
            self._audit("Distress signal detected: escalation path should stay available.")

        if "amount_above_guardian_limit" in risk_flags:
            self._audit("Amount exceeds Guardian limit: human review path required.")

        if "high_income_variance" in risk_flags:
            self._audit("Seasonality / income variance should be considered before flat repayment advice.")

        return case

    @listen(assess_risk)
    def scout_step(self, case):
        if self.state.get("consent_missing"):
            return case

        if contains_distress_signal(case.get("message", "")):
            self.state["scout_output"] = scout_agent_output(case)
            self._trace(
                "scout",
                "completed",
                "Scout engaged due to distress/support signal.",
            )
        else:
            self._trace(
                "scout",
                "skipped",
                "No distress signal detected.",
            )

        return case

    @listen(scout_step)
    def guardian_step(self, case):
        if self.state.get("consent_missing"):
            return case

        guardian_output = guardian_agent_output(case, self.state["risk_flags"])
        self.state["guardian_output"] = guardian_output

        self._audit("Occupation cannot be used as a standalone decision factor.")
        self._trace(
            "guardian",
            "completed",
            f"Guardian generated Tier-1 recommendation for route={self.state['route']}.",
        )

        return case

    @listen(guardian_step)
    def hunter_step(self, case):
        if self.state.get("consent_missing"):
            return case

        if self.state.get("route") != "guardian_tier1":
            hunter_output = hunter_agent_output(case, self.state["risk_flags"])
            self.state["hunter_output"] = hunter_output
            self.state["human_review_required"] = True
            self.state["human_checkpoint_required"] = True
            self.state["human_checkpoint_status"] = "awaiting_review"
            self.state["review_packet"] = {
                "member_name": case.get("member_name"),
                "county": case.get("county"),
                "livelihood": case.get("livelihood"),
                "amount_kes": case.get("amount_kes"),
                "risk_flags": self.state.get("risk_flags", []),
                "recommended_route": "human_review_queue",
                "reason": "Escalated due to policy/risk/welfare sensitivity.",
            }

            self._trace(
                "hunter",
                "completed",
                "Hunter prepared escalation briefing for human review.",
            )
        else:
            self._trace(
                "hunter",
                "skipped",
                "No escalation needed; case remained within bounded Tier-1 flow.",
            )

        return case

    @listen(hunter_step)
    def finalize(self, case):
        if self.state.get("consent_missing"):
            result = PrototypeResult(
                member_name=case.get("member_name", "Unknown"),
                route="hunter_escalation",
                risk_flags=["consent_missing"],
                scout_output=None,
                guardian_output=None,
                hunter_output="Processing paused: member consent missing. Route to human review and consent clarification.",
                human_review_required=True,
            )
        else:
            result = PrototypeResult(
                member_name=case.get("member_name", "Unknown"),
                route=self.state.get("route") or "hunter_escalation",
                risk_flags=self.state.get("risk_flags", []),
                scout_output=self.state.get("scout_output"),
                guardian_output=self.state.get("guardian_output"),
                hunter_output=self.state.get("hunter_output"),
                human_review_required=bool(self.state.get("human_review_required", False)),
            )

        self.state["final_result"] = asdict(result)
        self._trace(
            "finalize",
            "completed",
            f"Final route={result.route}; human_review_required={result.human_review_required}",
        )

        return asdict(result)


def apply_human_review_decision(
    flow_state: Dict[str, Any],
    decision: str,
    reviewer_note: str,
) -> Dict[str, Any]:
    updated = dict(flow_state)

    trace = list(updated.get("trace", []))
    audit_notes = list(updated.get("audit_notes", []))

    updated["human_checkpoint_status"] = decision
    updated["human_checkpoint_feedback"] = reviewer_note

    trace.append(
        {
            "step": "human_review_checkpoint",
            "status": "completed",
            "details": f"Decision={decision}; note={reviewer_note or 'none'}",
        }
    )

    audit_notes.append(f"Human reviewer decision: {decision}")
    if reviewer_note:
        audit_notes.append(f"Human reviewer note: {reviewer_note}")

    updated["trace"] = trace
    updated["audit_notes"] = audit_notes

    final_result = dict(updated.get("final_result", {}))
    final_result["human_reviewer_decision"] = decision
    final_result["human_reviewer_note"] = reviewer_note

    if decision == "approve_for_human_queue":
        final_result["post_review_status"] = "Queued for officer review"
    elif decision == "return_for_more_information":
        final_result["post_review_status"] = "Returned for more information"
    elif decision == "reject_recommendation":
        final_result["post_review_status"] = "AI recommendation rejected by human reviewer"
    else:
        final_result["post_review_status"] = "Human review completed"

    updated["final_result"] = final_result
    return updated


def run_case_with_flow(case: Dict[str, Any]) -> Tuple[PrototypeResult, Dict[str, Any]]:
    """
    Preferred path: explicit CrewAI Flow.
    Safe fallback: legacy direct runner.
    """
    if not CREWAI_FLOW_AVAILABLE:
        fallback = legacy_run_case(case)
        human_checkpoint_required = fallback.route != "guardian_tier1"
        fallback_state = {
            "id": None,
            "trace": [
                {
                    "step": "flow_bootstrap",
                    "status": "fallback",
                    "details": f"CrewAI Flow import unavailable; fallback runner used. Reason: {CREWAI_FLOW_ERROR}",
                }
            ],
            "audit_notes": [
                "CrewAI Flow is unavailable in this runtime; deterministic fallback was used."
            ],
            "risk_flags": fallback.risk_flags,
            "route": fallback.route,
            "human_review_required": fallback.human_review_required,
            "scout_output": fallback.scout_output,
            "guardian_output": fallback.guardian_output,
            "hunter_output": fallback.hunter_output,
            "human_checkpoint_required": human_checkpoint_required,
            "human_checkpoint_status": "awaiting_review" if human_checkpoint_required else "not_started",
            "human_checkpoint_feedback": None,
            "review_packet": {
                "member_name": case.get("member_name"),
                "county": case.get("county"),
                "livelihood": case.get("livelihood"),
                "amount_kes": case.get("amount_kes"),
                "risk_flags": fallback.risk_flags,
                "recommended_route": "human_review_queue" if human_checkpoint_required else "tier1_complete",
                "reason": "Fallback state generated for Streamlit HITL layer.",
            },
            "final_result": asdict(fallback),
        }
        return fallback, fallback_state

    try:
        flow = UjimaDecisionFlow(case)
        result = flow.kickoff()

        if isinstance(result, PrototypeResult):
            final_result = result
        else:
            final_result = PrototypeResult(**result)

        return final_result, dict(flow.state)

    except Exception as e:
        fallback = legacy_run_case(case)
        human_checkpoint_required = fallback.route != "guardian_tier1"
        fallback_state = {
            "id": None,
            "trace": [
                {
                    "step": "flow_bootstrap",
                    "status": "fallback",
                    "details": f"Flow unavailable; fallback runner used. Reason: {e}",
                }
            ],
            "audit_notes": [
                "Flow execution failed; deterministic/prototype fallback was used."
            ],
            "risk_flags": fallback.risk_flags,
            "route": fallback.route,
            "human_review_required": fallback.human_review_required,
            "scout_output": fallback.scout_output,
            "guardian_output": fallback.guardian_output,
            "hunter_output": fallback.hunter_output,
            "human_checkpoint_required": human_checkpoint_required,
            "human_checkpoint_status": "awaiting_review" if human_checkpoint_required else "not_started",
            "human_checkpoint_feedback": None,
            "review_packet": {
                "member_name": case.get("member_name"),
                "county": case.get("county"),
                "livelihood": case.get("livelihood"),
                "amount_kes": case.get("amount_kes"),
                "risk_flags": fallback.risk_flags,
                "recommended_route": "human_review_queue" if human_checkpoint_required else "tier1_complete",
                "reason": "Fallback state generated after Flow execution failure.",
            },
            "final_result": asdict(fallback),
        }
        return fallback, fallback_state
