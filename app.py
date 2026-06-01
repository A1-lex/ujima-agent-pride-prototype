from __future__ import annotations

import json
from dataclasses import asdict

import streamlit as st

from prototype import CASES_DIR, load_case, run_case


st.set_page_config(
    page_title="Ujima Agent Pride Demo",
    page_icon="🦁",
    layout="wide",
)

sample_files = {path.name: path for path in sorted(CASES_DIR.glob("*.json"))}

st.title("Ujima Agent Pride Demo")
st.caption("A simple deployed demo for the fictional Ujima SACCO capstone.")

st.info(
    "This demo shows a 3-agent workflow: Scout (literacy/distress detection), "
    "Guardian (Tier-1 triage), and Hunter (human-review coordination). "
    "It runs in deterministic template mode by default for stable deployment."
)

with st.sidebar:
    st.header("Demo Controls")
    sample_choice = st.selectbox("Load a sample case", ["Custom"] + list(sample_files.keys()))
    use_sample = sample_choice != "Custom"

sample = load_case(sample_files[sample_choice]) if use_sample else {}

with st.form("ujima_case_form"):
    st.subheader("Member Case Input")

    col1, col2 = st.columns(2)

    with col1:
        member_name = st.text_input("Member name", value=sample.get("member_name", ""))
        county = st.text_input("County", value=sample.get("county", "Kakamega"))
        livelihood = st.text_input("Livelihood", value=sample.get("livelihood", "market vendor"))
        product_type = st.text_input("Product type", value=sample.get("product_type", "school fees support"))
        amount_kes = st.number_input(
            "Requested amount (KES)",
            min_value=0,
            step=500,
            value=int(sample.get("amount_kes", 12000)),
        )

    with col2:
        children_under_5 = st.number_input(
            "Children under 5",
            min_value=0,
            step=1,
            value=int(sample.get("children_under_5", 0)),
        )
        current_savings_kes = st.number_input(
            "Current savings (KES)",
            min_value=0,
            step=100,
            value=int(sample.get("current_savings_kes", 0)),
        )
        income_variance = st.selectbox(
            "Income variance",
            ["low", "medium", "high"],
            index=["low", "medium", "high"].index(sample.get("income_variance", "medium"))
            if sample.get("income_variance", "medium") in ["low", "medium", "high"]
            else 1,
        )
        next_income_peak = st.text_input(
            "Next likely income peak",
            value=sample.get("next_income_peak", "October/November"),
        )
        repayment_history = st.selectbox(
            "Repayment history",
            ["good", "mixed", "poor"],
            index=["good", "mixed", "poor"].index(sample.get("repayment_history", "good"))
            if sample.get("repayment_history", "good") in ["good", "mixed", "poor"]
            else 0,
        )

    transaction_pattern = st.text_area(
        "Transaction pattern",
        value=sample.get(
            "transaction_pattern",
            "weekly inflows, stronger during harvest-linked trade periods",
        ),
        height=100,
    )

    message = st.text_area(
        "Member message",
        value=sample.get(
            "message",
            "Nataka mkopo wa school fees lakini naweza lipa kidogo kidogo bila stress.",
        ),
        height=100,
    )

    consent_status = st.checkbox("Member consent confirmed", value=bool(sample.get("consent_status", True)))

    submitted = st.form_submit_button("Run Agent Pride Demo")

if submitted:
    case = {
        "member_name": member_name,
        "county": county,
        "livelihood": livelihood,
        "product_type": product_type,
        "amount_kes": amount_kes,
        "children_under_5": children_under_5,
        "current_savings_kes": current_savings_kes,
        "income_variance": income_variance,
        "next_income_peak": next_income_peak,
        "transaction_pattern": transaction_pattern,
        "repayment_history": repayment_history,
        "consent_status": consent_status,
        "message": message,
    }

    result = run_case(case)
    result_dict = asdict(result)

    st.subheader("Decision Summary")

    col_route, col_review, col_flags = st.columns(3)
    with col_route:
        st.metric("Route", result.route)
    with col_review:
        st.metric("Human review required", "Yes" if result.human_review_required else "No")
    with col_flags:
        st.metric("Risk flags", len(result.risk_flags))

    if result.route == "guardian_tier1":
        st.success("This case stayed within bounded Tier-1 triage.")
    else:
        st.warning("This case escalated for human-in-the-loop review.")

    st.markdown("### Risk Flags")
    if result.risk_flags:
        for flag in result.risk_flags:
            st.write(f"- {flag}")
    else:
        st.write("- none")

    tab_scout, tab_guardian, tab_hunter, tab_raw = st.tabs(
        ["Scout Output", "Guardian Output", "Hunter Output", "Raw JSON"]
    )

    with tab_scout:
        if result.scout_output:
            st.code(result.scout_output, language="text")
        else:
            st.write("No Scout message was needed for this case.")

    with tab_guardian:
        if result.guardian_output:
            st.code(result.guardian_output, language="text")
        else:
            st.write("No Guardian output available.")

    with tab_hunter:
        if result.hunter_output:
            st.code(result.hunter_output, language="text")
        else:
            st.write("No Hunter escalation was needed for this case.")

    with tab_raw:
        st.json(result_dict)

    st.download_button(
        label="Download result JSON",
        data=json.dumps(result_dict, indent=2, ensure_ascii=False),
        file_name=f"{member_name.lower().replace(' ', '_')}_ujima_result.json",
        mime="application/json",
    )

st.markdown("---")
st.caption(
    "Case note: Ujima is a fictional Kenyan SACCO case used for instructional design. "
    "This app is a demonstration of bounded multi-agent orchestration, not a production lending system."
)