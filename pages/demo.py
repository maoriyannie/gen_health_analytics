"""
pages/Demo.py — Pre-seeded demo dashboard for Gen-Health Analytics.
No data entry required; showcases all three built-in risk scenarios.
"""

import streamlit as st
from engine.risk_scorer import score
from app import (
    _render_summary,
    _risk_gauge,
    _onset_trend_chart,
    _genogram,
    _render_alerts,
    PRIORITY_COLOR,
)
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Seed data — mirrors the three scenarios documented in app.py how-to-use
# ---------------------------------------------------------------------------

SCENARIOS = {
    "BRCA Cancer Risk": {
        "description": "32-year-old female — two first/second-degree relatives with breast cancer under 50 and a grandmother with ovarian cancer. Triggers HIGH-priority BRCA alerts.",
        "payload": {
            "proband_age": 32,
            "proband_sex": "female",
            "conditions_of_interest": ["breast_cancer", "ovarian_cancer", "diabetes"],
            "family_members": [
                {
                    "name": "Patricia",
                    "relationship": "mother",
                    "sex": "female",
                    "is_deceased": False,
                    "conditions": [{"condition_name": "breast_cancer", "age_of_onset": 44, "confirmed": True, "cause_of_death": False}],
                    "lifestyle_flags": {},
                },
                {
                    "name": "Susan",
                    "relationship": "maternal_aunt",
                    "sex": "female",
                    "is_deceased": False,
                    "conditions": [{"condition_name": "breast_cancer", "age_of_onset": 48, "confirmed": True, "cause_of_death": False}],
                    "lifestyle_flags": {},
                },
                {
                    "name": "Helen",
                    "relationship": "maternal_grandmother",
                    "sex": "female",
                    "is_deceased": True,
                    "conditions": [{"condition_name": "ovarian_cancer", "age_of_onset": 60, "confirmed": True, "cause_of_death": True}],
                    "lifestyle_flags": {},
                },
            ],
        },
        "members_table": [
            {"Member": "Patricia", "Relationship": "Mother", "Condition": "Breast cancer", "Age of onset": 44, "Lifestyle flags": "—"},
            {"Member": "Susan", "Relationship": "Maternal aunt", "Condition": "Breast cancer", "Age of onset": 48, "Lifestyle flags": "—"},
            {"Member": "Helen †", "Relationship": "Maternal grandmother", "Condition": "Ovarian cancer", "Age of onset": 60, "Lifestyle flags": "—"},
        ],
    },
    "Early-Onset Heart Disease": {
        "description": "38-year-old male — father, grandfather, and uncle all had heart disease in their 40s–50s. Onset is accelerating each generation.",
        "payload": {
            "proband_age": 38,
            "proband_sex": "male",
            "conditions_of_interest": ["heart_disease", "hypertension"],
            "family_members": [
                {
                    "name": "James",
                    "relationship": "father",
                    "sex": "male",
                    "is_deceased": False,
                    "conditions": [{"condition_name": "heart_disease", "age_of_onset": 48, "confirmed": True, "cause_of_death": False}],
                    "lifestyle_flags": {"High_BP": True, "Smoking": True},
                },
                {
                    "name": "Robert",
                    "relationship": "paternal_grandfather",
                    "sex": "male",
                    "is_deceased": True,
                    "conditions": [{"condition_name": "heart_disease", "age_of_onset": 55, "confirmed": True, "cause_of_death": False}],
                    "lifestyle_flags": {},
                },
                {
                    "name": "Michael",
                    "relationship": "paternal_uncle",
                    "sex": "male",
                    "is_deceased": False,
                    "conditions": [{"condition_name": "heart_disease", "age_of_onset": 51, "confirmed": True, "cause_of_death": False}],
                    "lifestyle_flags": {},
                },
            ],
        },
        "members_table": [
            {"Member": "James", "Relationship": "Father", "Condition": "Heart disease", "Age of onset": 48, "Lifestyle flags": "High BP, Smoking"},
            {"Member": "Robert †", "Relationship": "Paternal grandfather", "Condition": "Heart disease", "Age of onset": 55, "Lifestyle flags": "—"},
            {"Member": "Michael", "Relationship": "Paternal uncle", "Condition": "Heart disease", "Age of onset": 51, "Lifestyle flags": "—"},
        ],
    },
    "Diabetes — Lifestyle vs Genetic": {
        "description": "45-year-old female — mother, grandmother, and sister all have diabetes with overlapping lifestyle factors (High BP). Environmental score dominates over genetic.",
        "payload": {
            "proband_age": 45,
            "proband_sex": "female",
            "conditions_of_interest": ["diabetes", "heart_disease"],
            "family_members": [
                {
                    "name": "Linda",
                    "relationship": "mother",
                    "sex": "female",
                    "is_deceased": False,
                    "conditions": [{"condition_name": "diabetes", "age_of_onset": 52, "confirmed": True, "cause_of_death": False}],
                    "lifestyle_flags": {"HighBP": True, "HighChol": True},
                },
                {
                    "name": "Dorothy",
                    "relationship": "maternal_grandmother",
                    "sex": "female",
                    "is_deceased": True,
                    "conditions": [{"condition_name": "diabetes", "age_of_onset": 60, "confirmed": True, "cause_of_death": False}],
                    "lifestyle_flags": {"HighBP": True},
                },
                {
                    "name": "Carol",
                    "relationship": "sister",
                    "sex": "female",
                    "is_deceased": False,
                    "conditions": [{"condition_name": "diabetes", "age_of_onset": 40, "confirmed": True, "cause_of_death": False}],
                    "lifestyle_flags": {"HighBP": True, "Smoker": True},
                },
            ],
        },
        "members_table": [
            {"Member": "Linda", "Relationship": "Mother", "Condition": "Diabetes", "Age of onset": 52, "Lifestyle flags": "High BP, High Chol"},
            {"Member": "Dorothy †", "Relationship": "Maternal grandmother", "Condition": "Diabetes", "Age of onset": 60, "Lifestyle flags": "High BP"},
            {"Member": "Carol", "Relationship": "Sister", "Condition": "Diabetes", "Age of onset": 40, "Lifestyle flags": "High BP, Smoker"},
        ],
    },
}

# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Demo — Gen-Health Analytics",
    page_icon="🧬",
    layout="wide",
)

st.title("Gen-Health Analytics — Demo")
st.markdown(
    "Explore the dashboard with pre-loaded family histories. "
    "No data entry needed. Switch scenarios below to see how different hereditary patterns affect the risk output."
)
st.info("This is a **read-only demo**. To analyse your own family history, use the main app from the sidebar.")

st.divider()

# Scenario selector
scenario_name = st.radio(
    "Choose a scenario",
    list(SCENARIOS.keys()),
    horizontal=True,
)

scenario = SCENARIOS[scenario_name]

st.caption(scenario["description"])

# Seeded family members table
with st.expander("What's in this scenario?", expanded=False):
    st.dataframe(
        scenario["members_table"],
        use_container_width=True,
        hide_index=True,
    )

st.divider()

# Run analysis
try:
    result = score(scenario["payload"])
except ValueError as e:
    st.error(f"Engine error: {e}")
    st.stop()

members = scenario["payload"]["family_members"]

# Summary metrics
_render_summary(result)

tab_risk, tab_trend, tab_tree, tab_alerts, tab_json = st.tabs(
    ["Risk Gauges", "Onset Trends", "Family Tree", "Alerts", "Raw JSON"]
)

CANCER_CONDITIONS = {
    "breast_cancer", "ovarian_cancer", "male_breast_cancer",
    "colorectal_cancer", "colon_cancer", "rectal_cancer",
}

with tab_risk:
    conditions = result["conditions"]
    numeric_conditions = {k: v for k, v in conditions.items() if k not in CANCER_CONDITIONS}
    cancer_conditions  = {k: v for k, v in conditions.items() if k in CANCER_CONDITIONS}

    if numeric_conditions:
        cols = st.columns(min(len(numeric_conditions), 3))
        for idx, (cond_name, cdata) in enumerate(numeric_conditions.items()):
            with cols[idx % len(cols)]:
                st.plotly_chart(
                    _risk_gauge(
                        cond_name,
                        cdata.get("genetic_predisposition_score", 0),
                        cdata.get("environmental_risk_score", 0),
                        cdata.get("relative_risk_ratio", 1.0),
                    ),
                    use_container_width=True,
                )
        st.caption(
            "**Genetic score** (0–100): hereditary contribution to excess risk. "
            "**Environmental score** (0–100): shared lifestyle contribution. "
            "**RR**: relative risk vs. general population."
        )

    if cancer_conditions:
        if numeric_conditions:
            st.divider()
        st.markdown("#### Cancer Risk (NCCN Rule-Based Assessment)")
        cancer_cols = st.columns(min(len(cancer_conditions), 3))
        for idx, (cond_name, cdata) in enumerate(cancer_conditions.items()):
            with cancer_cols[idx % len(cancer_cols)]:
                flags      = cdata.get("cancer_flags", [])
                high_flags = [f for f in flags if f.get("priority") == "high"]
                med_flags  = [f for f in flags if f.get("priority") == "medium"]
                affected_count = cdata.get("affected_relatives_count", 0)

                title = cond_name.replace("_", " ").title()
                if high_flags:
                    border_color = "#e63946"
                    badge = '<span style="color:#e63946;font-weight:bold;">HIGH RISK</span>'
                    flag_count = len(high_flags)
                elif med_flags:
                    border_color = "#f4a261"
                    badge = '<span style="color:#f4a261;font-weight:bold;">MODERATE RISK</span>'
                    flag_count = len(med_flags)
                else:
                    border_color = "#2a9d8f"
                    badge = '<span style="color:#2a9d8f;font-weight:bold;">NO FLAGS</span>'
                    flag_count = 0

                reasons = "<br>".join(
                    f"• {f['trigger_reason']}" for f in (high_flags or med_flags)
                ) or "No NCCN red flag criteria met based on entered family history."

                st.markdown(
                    f"""
                    <div style="border-left: 5px solid {border_color}; padding: 14px 16px;
                                background: #1e1e1e; border-radius: 6px; margin-bottom: 8px;">
                        <div style="font-size:15px;font-weight:bold;margin-bottom:4px;">{title}</div>
                        {badge} &nbsp;·&nbsp;
                        <span style="color:#aaa;">{affected_count} affected relative(s)</span>
                        &nbsp;·&nbsp;
                        <span style="color:#aaa;">{flag_count} NCCN flag(s) triggered</span>
                        <div style="margin-top:8px;color:#ccc;font-size:13px;">{reasons}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        st.caption(
            "Cancer risk uses NCCN Clinical Practice Guidelines (rule-based). "
            "No population RR is computed — see the **Alerts** tab for recommended actions."
        )

with tab_trend:
    st.plotly_chart(_onset_trend_chart(result["conditions"]), use_container_width=True)
    st.caption(
        "Dotted lines show the OLS trend projected toward your generation. "
        "A negative slope means the condition is appearing earlier each generation."
    )

with tab_tree:
    st.plotly_chart(_genogram(result, members), use_container_width=True)

with tab_alerts:
    _render_alerts(result["red_flag_alerts"])

with tab_json:
    st.json(result)
