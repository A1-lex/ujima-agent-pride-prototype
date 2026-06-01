from __future__ import annotations

from typing import Dict, List


FLAG_EXPLANATIONS = {
    "amount_above_guardian_limit": {
        "title": "This request needs a deeper review",
        "member_text": "Your request amount is above the fast-track limit, so a human loan officer should review it carefully instead of relying on an automatic first-pass decision.",
        "next_step": "A loan officer should confirm whether timing, purpose, and repayment structure are suitable.",
    },
    "young_children_welfare_sensitivity": {
        "title": "Household welfare needs extra care",
        "member_text": "Because this case may affect a household with young children, the system should slow down and make sure repayment pressure does not create harm.",
        "next_step": "Review repayment timing and hardship sensitivity before any final outcome.",
    },
    "high_income_variance": {
        "title": "Income may be seasonal rather than weak",
        "member_text": "Your cash flow may rise and fall during the year. That does not automatically mean you are unsafe to lend to, but it does mean repayment timing should match stronger income periods.",
        "next_step": "Check seasonal peaks and consider a repayment plan that follows actual income rhythms.",
    },
    "distress_signal_detected": {
        "title": "Urgency or distress was detected",
        "member_text": "The message suggests financial pressure or urgency. This is a sign that human support may be needed quickly, especially to avoid harmful borrowing options.",
        "next_step": "Escalate promptly and offer a respectful human review path.",
    },
    "repayment_history_mixed": {
        "title": "Repayment history needs context",
        "member_text": "Past repayment patterns may need clarification before a decision is made. Mixed history should trigger review, not automatic judgment.",
        "next_step": "Ask what changed, check recent behavior, and review whether timing or hardship explains the pattern.",
    },
    "consent_missing": {
        "title": "Consent must be confirmed first",
        "member_text": "This case cannot move forward properly until the member’s consent status is clear.",
        "next_step": "Pause processing and confirm consent.",
    },
}


def explain_risk_flags(risk_flags: List[str]) -> List[Dict[str, str]]:
    cards = []
    for flag in risk_flags:
        item = FLAG_EXPLANATIONS.get(
            flag,
            {
                "title": flag.replace("_", " ").title(),
                "member_text": "This factor requires additional review.",
                "next_step": "Review manually.",
            },
        )
        cards.append({"flag": flag, **item})
    return cards


def overall_explanation(route: str, risk_flags: List[str]) -> str:
    if route == "guardian_tier1" and not risk_flags:
        return (
            "This case stayed within bounded Tier-1 triage because no major escalation signals were detected. "
            "The next step is to confirm repayment timing and communicate clearly."
        )

    if "high_income_variance" in risk_flags:
        return (
            "This case appears to require more context rather than a flat yes/no judgment. "
            "Seasonal or uneven income should be interpreted carefully before repayment expectations are set."
        )

    if "distress_signal_detected" in risk_flags:
        return (
            "This case includes urgency or distress signals, so human review is important to prevent harm and offer support quickly."
        )

    return (
        "This case needs additional context before any final decision should be trusted. "
        "Human review helps make the result fairer and easier to explain."
    )
