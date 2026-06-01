from __future__ import annotations

import json
import os
from dataclasses import asdict

import streamlit as st

from prototype import CASES_DIR, load_case
from ujima_flow import apply_human_review_decision, run_case_with_flow


st.set_page_config(
    page_title="Ujima Agent Pride Demo",
    page_icon="🦁",
    layout="wide",
)

if "OPENAI_API_KEY" in st.secrets:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

if "MODEL_NAME" in st.secrets:
    os.environ["MODEL_NAME"] = st.secrets["MODEL_NAME"]

os.environ["USE_CREWAI"] = str(st.secrets.get("USE_CREWAI", False)).lower()

LIVE_LLM_MODE = (
    os.environ.get("USE_CREWAI", "false").lower() == "true"
    and bool(os.environ.get("OPENAI_API_KEY"))
)

if "latest_result" not in st.session_state:
    st.session_state.latest_result = None

if "latest_flow_state" not in st.session_state:
    st.session_state.latest_flow_state = None

if "latest_member_name" not in st.session_state:
    st.session_state.latest_member_name = None

if "latest_review_action" not in st.session_state:
    st.session_state.latest_review_action = None

if "latest_review_note" not in st.session_state:
    st.session_state.latest_review_note = None

# ---------- Styling ----------
st.markdown(
    """
    <style>
    .hero {
        padding: 1.2rem 1.4rem;
        border-radius: 16px;
        background: linear-gradient(135deg, #0F766E 0%, #115E59 100%);
        color: white;
        margin-bottom: 1rem;
    }
    .card {
        background: #ffffff;
        padding: 1rem;
        border-radius: 14px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        margin-bottom: 0.8rem;
    }
    .agent-scout {
        border-left: 6px solid #16A34A;
    }
    .agent-guardian {
        border-left: 6px solid #D97706;
    }
    .agent-hunter {
        border-left: 6px solid #1D4ED8;
    }
    .route-ok {
        background: #ECFDF5;
        color: #065F46;
        padding: 0.9rem 1rem;
        border-radius: 12px;
        border: 1px solid #A7F3D0;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .route-escalate {
        background: #FFF7ED;
        color: #9A3412;
        padding: 0.9rem 1rem;
        border-radius: 12px;
        border: 1px solid #FDBA74;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .small-note {
        font-size: 0.92rem;
        color: #4B5563;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

sample_files = {path.name: path for path in sorted(CASES_DIR.glob("*.json"))}

# ---------- Sidebar ----------
with st.sidebar:
    st.title("Demo Controls")
    sample_choice = st.selectbox(
        "Load a sample case",
        ["Custom"] + list(sample_files.keys()),
    )
    use_sample = sample_choice != "Custom"

    st.markdown("---")
    st.subheader("About this demo")
    st.caption(
        "Fictional Kenyan SACCO case. "
        "Shows a 3-agent workflow with bounded autonomy, fairness-aware routing, and human escalation."
    )

    st.markdown("---")
    st.subheader("Engine status")
    if LIVE_LLM_MODE:
        st.success("Live CrewAI/OpenAI mode enabled")
        st.caption(f"Model: {os.environ.get('MODEL_NAME', 'gpt-4o-mini')}")
    else:
        st.info("Template fallback mode enabled")
        st.caption("Add secrets to activate real CrewAI/OpenAI outputs.")

    st.markdown("**Agents**")
    st.write("• Scout — literacy & distress detection")
    st.write("• Guardian — Tier-1 triage")
    st.write("• Hunter — human-review coordination")

    st.markdown("---")
    st.subheader("Safety defaults")
    st.write("• No occupation-only decisions")
    st.write("• Distress triggers escalation")
    st.write("• High-stakes cases require human review")
    st.write("• Non-shaming communication only")
    st.write("• Escalated cases can pause for human checkpoint review")

sample = load_case(sample_files[sample_choice]) if use_sample else {}

# ---------- Header ----------
st.markdown(
    """
    <div class="hero">
        <h1 style="margin-bottom: 0.3rem;">Ujima Agent Pride Demo</h1>
        <div style="font-size: 1.05rem;">
            A simple deployed demo of a 3-agent SACCO workflow:
            <b>Scout</b> → <b>Guardian</b> → <b>Hunter</b>
        </div>
        <div style="margin-top: 0.5rem; opacity: 0.95;">
            Focus: fair triage, distress detection, human-in-the-loop escalation, and dignity-preserving outputs
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Sample cases", len(sample_files))
m2.metric("Deployment mode", "Live")
m3.metric("Current engine", "CrewAI / OpenAI" if LIVE_LLM_MODE else "Template mode")
m4.metric("Human override", "Enabled")
m5.metric("Orchestration", "Flow-first")

st.markdown("### Agent Roles")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(
        """
        <div class="card agent-scout">
            <h4>Scout Agent</h4>
            <p>Financial literacy coach and early distress detector.</p>
            <p class="small-note">Looks for signals like school-fee stress, loan-shark mention, or panic language.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        """
        <div class="card agent-guardian">
            <h4>Guardian Agent</h4>
            <p>Bounded Tier-1 triage agent.</p>
            <p class="small-note">Handles lower-risk screening while checking seasonality, affordability, and risk flags.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        """
        <div class="card agent-hunter">
            <h4>Hunter Agent</h4>
            <p>Human-in-the-loop coordinator.</p>
            <p class="small-note">Prepares briefing support for complex or welfare-sensitive cases without making the final decision.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with st.expander("How this workflow maps to the capstone"):
    st.write(
        """
        - Scout handles literacy support and catches distress signals early.
        - Guardian performs first-pass triage for lower-risk cases.
        - Hunter takes over when the case is high-value, complex, or welfare-sensitive.
        - A human officer remains accountable for escalated outcomes.
        """
    )

# ---------- Form ----------
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
        height=90,
    )

    message = st.text_area(
        "Member message",
        value=sample.get(
            "message",
            "Nataka mkopo wa school fees lakini naweza lipa kidogo kidogo bila stress.",
        ),
        height=90,
    )

    consent_status = st.checkbox(
        "Member consent confirmed",
        value=bool(sample.get("consent_status", True)),
    )

    submitted = st.form_submit_button("Run Agent Pride Demo")

# ---------- Results ----------
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

    result, flow_state = run_case_with_flow(case)
    result_dict = asdict(result)

    st.session_state.latest_result = result_dict
    st.session_state.latest_flow_state = flow_state
    st.session_state.latest_member_name = member_name
    st.session_state.latest_review_action = None
    st.session_state.latest_review_note = None

    st.subheader("Decision Summary")

    if result.route == "guardian_tier1":
        st.markdown(
            '<div class="route-ok">Route result: Guardian handled this as a bounded Tier-1 case.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="route-escalate">Route result: This case escalated for human-in-the-loop review.</div>',
            unsafe_allow_html=True,
        )

    r1, r2, r3 = st.columns(3)
    r1.metric("Route", result.route)
    r2.metric("Human review required", "Yes" if result.human_review_required else "No")
    r3.metric("Risk flags", len(result.risk_flags))

    s1, s2 = st.columns(2)

    with s1:
        st.markdown("#### Member Snapshot")
        st.write(f"**Name:** {member_name}")
        st.write(f"**County:** {county}")
        st.write(f"**Livelihood:** {livelihood}")
        st.write(f"**Requested amount:** KES {amount_kes:,}")
        st.write(f"**Children under 5:** {children_under_5}")
        st.write(f"**Consent status:** {'Confirmed' if consent_status else 'Missing'}")

    with s2:
        st.markdown("#### Governance Snapshot")
        st.write("**Proxy rule:** occupation cannot be used alone")
        st.write("**Distress rule:** distress triggers escalation")
        st.write("**Welfare rule:** sensitive cases require human review")
        st.write("**Tone rule:** no humiliating denial language")
        st.write(f"**Mode:** {'live CrewAI/OpenAI mode' if LIVE_LLM_MODE else 'deterministic / stable demo mode'}")
        st.write(f"**Flow state ID:** {flow_state.get('id', 'Not available')}")

    t1, t2, t3, t4 = st.tabs(
        ["Decision Path", "Agent Outputs", "Execution Trace", "Raw JSON / Download"]
    )

    with t1:
        st.markdown("#### Workflow Path")

        scout_triggered = bool(result.scout_output)
        guardian_ran = bool(result.guardian_output)
        hunter_ran = bool(result.hunter_output)

        if scout_triggered:
            st.info("Step 1 — Scout engaged because the case contained a distress or support signal.")
        else:
            st.write("Step 1 — Scout did not need to send a direct message for this case.")

        if guardian_ran:
            st.success("Step 2 — Guardian performed Tier-1 triage and generated a bounded recommendation.")

        if hunter_ran:
            st.warning("Step 3 — Hunter prepared the case for human review.")
        else:
            st.write("Step 3 — No Hunter escalation was needed.")

        st.markdown("#### Risk Flags")
        if result.risk_flags:
            for flag in result.risk_flags:
                st.write(f"- {flag}")
        else:
            st.write("- none")

    with t2:
        if result.scout_output:
            st.markdown("#### Scout Output")
            st.code(result.scout_output, language="text")

        if result.guardian_output:
            st.markdown("#### Guardian Output")
            st.code(result.guardian_output, language="text")

        if result.hunter_output:
            st.markdown("#### Hunter Output")
            st.code(result.hunter_output, language="text")

    with t3:
        st.markdown("#### Flow Execution Trace")
        trace = flow_state.get("trace", [])
        if trace:
            for i, item in enumerate(trace, start=1):
                st.write(f"**{i}. {item.get('step', 'step')}**")
                st.write(f"- status: {item.get('status', 'unknown')}")
                st.write(f"- details: {item.get('details', '')}")
        else:
            st.write("No trace available.")

        st.markdown("#### Audit Notes")
        audit_notes = flow_state.get("audit_notes", [])
        if audit_notes:
            for note in audit_notes:
                st.write(f"- {note}")
        else:
            st.write("- none")

    with t4:
        st.markdown("#### Result JSON")
        st.json(result_dict)

        st.markdown("#### Flow State JSON")
        st.json(flow_state)

        st.download_button(
            label="Download result JSON",
            data=json.dumps(result_dict, indent=2, ensure_ascii=False),
            file_name=f"{member_name.lower().replace(' ', '_')}_ujima_result.json",
            mime="application/json",
        )

        st.download_button(
            label="Download flow state JSON",
            data=json.dumps(flow_state, indent=2, ensure_ascii=False, default=str),
            file_name=f"{member_name.lower().replace(' ', '_')}_ujima_flow_state.json",
            mime="application/json",
        )

if st.session_state.latest_flow_state:
    flow_state = st.session_state.latest_flow_state
    latest_result = st.session_state.latest_result or {}

    if flow_state.get("human_checkpoint_required") and flow_state.get("human_checkpoint_status") == "awaiting_review":
        st.markdown("## Human Review Checkpoint")
        st.warning("This case requires a human checkpoint before the workflow can be considered complete.")

        review_packet = flow_state.get("review_packet", {})

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Review Packet")
            st.write(f"**Member:** {review_packet.get('member_name', 'Unknown')}")
            st.write(f"**County:** {review_packet.get('county', 'Unknown')}")
            st.write(f"**Livelihood:** {review_packet.get('livelihood', 'Unknown')}")
            st.write(f"**Amount:** KES {review_packet.get('amount_kes', 0):,}")
        with c2:
            st.markdown("### Escalation Reasoning")
            st.write(f"**Recommended route:** {review_packet.get('recommended_route', 'n/a')}")
            st.write(f"**Reason:** {review_packet.get('reason', 'n/a')}")
            risk_flags = review_packet.get("risk_flags", [])
            st.write(f"**Risk flags:** {', '.join(risk_flags) if risk_flags else 'none'}")

        with st.form("human_review_form"):
            decision = st.radio(
                "Reviewer decision",
                [
                    "approve_for_human_queue",
                    "return_for_more_information",
                    "reject_recommendation",
                ],
                help="This simulates the PRIDE pause-point / human review checkpoint.",
            )
            reviewer_note = st.text_area(
                "Reviewer note",
                placeholder="Example: Escalate to officer Sarah due to school-fee timing mismatch and welfare sensitivity.",
            )
            review_submit = st.form_submit_button("Submit Human Review Decision")

        if review_submit:
            updated_state = apply_human_review_decision(
                flow_state=flow_state,
                decision=decision,
                reviewer_note=reviewer_note,
            )
            st.session_state.latest_flow_state = updated_state
            st.session_state.latest_review_action = decision
            st.session_state.latest_review_note = reviewer_note
            st.success("Human review decision recorded. Refreshing the workflow state.")
            st.rerun()

    elif flow_state.get("human_checkpoint_required"):
        st.markdown("## Human Review Outcome")
        final_result = flow_state.get("final_result", {})
        st.success("Human checkpoint completed.")

        st.write(f"**Decision:** {flow_state.get('human_checkpoint_status', 'unknown')}")
        st.write(f"**Reviewer note:** {flow_state.get('human_checkpoint_feedback', 'none')}")
        st.write(f"**Post-review status:** {final_result.get('post_review_status', 'n/a')}")

        st.markdown("### Updated Trace")
        trace = flow_state.get("trace", [])
        if trace:
            for i, item in enumerate(trace, start=1):
                st.write(f"**{i}. {item.get('step', 'step')}**")
                st.write(f"- status: {item.get('status', 'unknown')}")
                st.write(f"- details: {item.get('details', '')}")
        else:
            st.write("No trace available.")

        st.markdown("### Updated Audit Notes")
        audit_notes = flow_state.get("audit_notes", [])
        if audit_notes:
            for note in audit_notes:
                st.write(f"- {note}")
        else:
            st.write("- none")

st.markdown("---")
st.caption(
    "Case note: Ujima is a fictional Kenyan SACCO case used for instructional design. "
    "This app demonstrates bounded multi-agent orchestration, not a production lending system."
)