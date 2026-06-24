"""
app.py — Gen-Health Analytics Streamlit Dashboard
Run: streamlit run app.py
"""

import streamlit as st
import plotly.graph_objects as go
from engine.risk_scorer import score

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RELATIONSHIPS = [
    "father", "mother", "brother", "sister",
    "paternal_grandfather", "paternal_grandmother",
    "maternal_grandfather", "maternal_grandmother",
    "paternal_uncle", "paternal_aunt",
    "maternal_uncle", "maternal_aunt",
    "son", "daughter",
    "half_brother", "half_sister",
    "grandfather", "grandmother",
    "great_uncle", "great_aunt", "first_cousin",
    "stepfather", "stepmother",
    # Third generation (great-grandparents)
    "paternal_great_grandfather", "paternal_great_grandmother",
    "maternal_great_grandfather", "maternal_great_grandmother",
]

ETHNICITIES = [
    "not specified",
    "ashkenazi_jewish",
    "icelandic",
    "other",
]

CONDITIONS = [
    "diabetes",
    "heart_disease",
    "breast_cancer",
    "ovarian_cancer",
    "male_breast_cancer",
    "colorectal_cancer",
    "hypertension",
]

CVD_FLAGS = [
    "Smoking", "Obesity", "Sedentary_Lifestyle",
    "High_BP", "High_Cholesterol", "Chronic_Stress", "Diabetes",
]

DIABETES_FLAGS = [
    "HighBP", "HighChol", "Smoker",
    "PhysInactivity", "HvyAlcoholConsump",
]

RELATIONSHIP_SEX = {
    "father": "male",            "mother": "female",
    "brother": "male",           "sister": "female",
    "paternal_grandfather": "male",  "paternal_grandmother": "female",
    "maternal_grandfather": "male",  "maternal_grandmother": "female",
    "paternal_uncle": "male",    "paternal_aunt": "female",
    "maternal_uncle": "male",    "maternal_aunt": "female",
    "son": "male",               "daughter": "female",
    "half_brother": "male",      "half_sister": "female",
    "grandfather": "male",       "grandmother": "female",
    "uncle": "male",             "aunt": "female",
    "great_uncle": "male",       "great_aunt": "female",
    "stepfather": "male",        "stepmother": "female",
    "paternal_great_grandfather": "male",  "paternal_great_grandmother": "female",
    "maternal_great_grandfather": "male",  "maternal_great_grandmother": "female",
    "great_grandfather": "male", "great_grandmother": "female",
}

PRIORITY_COLOR = {"high": "#e63946", "medium": "#f4a261", "low": "#2a9d8f"}

GENERATION_LABEL = {
    -3: "Great-Grandparents",
    -2: "Grandparents",
    -1: "Parents / Aunts / Uncles",
     0: "You & Siblings",
     1: "Children",
}

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

def _init_state():
    if "members" not in st.session_state:
        st.session_state.members = []
    if "result" not in st.session_state:
        st.session_state.result = None


# ---------------------------------------------------------------------------
# Sidebar — data entry form
# ---------------------------------------------------------------------------

def _render_sidebar():
    st.sidebar.title("Family Health Input")

    st.sidebar.subheader("Your Info (Proband)")
    proband_age = st.sidebar.number_input("Your age", min_value=1, max_value=120, value=34)
    proband_sex = st.sidebar.selectbox("Biological sex", ["female", "male", "other", "unknown"])
    proband_ethnicity = st.sidebar.selectbox(
        "Ancestry / ethnicity (optional)",
        ETHNICITIES,
        help="Some ancestries carry known genetic risk variants (e.g. BRCA founder mutations in Ashkenazi Jewish populations). Select if applicable.",
    )

    st.sidebar.subheader("Conditions to Analyse")
    selected_conditions = st.sidebar.multiselect(
        "Select conditions",
        CONDITIONS,
        default=["diabetes", "heart_disease"],
    )

    st.sidebar.divider()
    st.sidebar.subheader("Family Members")

    # Add / remove members
    if st.sidebar.button("+ Add family member"):
        st.session_state.members.append({
            "name": "",
            "relationship": "father",
            "sex": "male",
            "is_deceased": False,
            "conditions": [],
            "lifestyle_flags": {},
        })

    for i, member in enumerate(st.session_state.members):
        cond_summary = ", ".join(c["condition_name"].replace("_", " ") for c in member["conditions"])
        expander_label = (
            f"{member.get('name') or member['relationship']}"
            + (f" — {cond_summary}" if cond_summary else "")
        )
        with st.sidebar.expander(f"Member {i + 1}: {expander_label}", expanded=False, key=f"exp_{i}"):
            member["name"] = st.text_input("Name (optional)", value=member["name"], key=f"name_{i}")
            member["relationship"] = st.selectbox(
                "Relationship", RELATIONSHIPS,
                index=RELATIONSHIPS.index(member["relationship"]) if member["relationship"] in RELATIONSHIPS else 0,
                key=f"rel_{i}",
            )

            inferred_sex = RELATIONSHIP_SEX.get(member["relationship"])
            if inferred_sex:
                member["sex"] = inferred_sex
                st.session_state[f"sex_{i}"] = inferred_sex

            col_sex, col_dec = st.columns(2)
            member["sex"] = col_sex.selectbox(
                "Sex", ["male", "female", "other", "unknown"],
                index=["male", "female", "other", "unknown"].index(member["sex"]),
                key=f"sex_{i}",
                disabled=inferred_sex is not None,
            )
            member["is_deceased"] = col_dec.checkbox("Deceased", value=member["is_deceased"], key=f"dec_{i}")

            st.markdown("**Conditions**")
            # Existing conditions list
            for ci, c in enumerate(member["conditions"]):
                cols = st.columns([3, 2, 1])
                cols[0].caption(c["condition_name"].replace("_", " "))
                cols[1].caption(f"onset: {c['age_of_onset'] or '?'}")
                if cols[2].button("✕", key=f"remcond_{i}_{ci}"):
                    member["conditions"].pop(ci)
                    st.rerun()
                if member["is_deceased"]:
                    c["cause_of_death"] = st.checkbox(
                        f"Cause of death ({c['condition_name']})",
                        value=c.get("cause_of_death", False),
                        key=f"cod_{i}_{ci}",
                    )

            # Add new condition row
            col_cond, col_age = st.columns([3, 2])
            cond_name = col_cond.selectbox("Add condition", [""] + CONDITIONS, key=f"cname_{i}")
            cond_onset = col_age.number_input("Age onset", min_value=0, max_value=120, value=0, key=f"onset_{i}")
            if st.button("+ Add", key=f"addcond_{i}"):
                if cond_name:
                    member["conditions"].append({
                        "condition_name": cond_name,
                        "age_of_onset": cond_onset if cond_onset > 0 else None,
                        "confirmed": True,
                        "cause_of_death": False,
                    })
                    st.rerun()

            # Lifestyle flags — show flags relevant to this member's conditions
            relevant_flags = set()
            for c in member["conditions"]:
                cn = c["condition_name"]
                if cn in ("heart_disease", "cardiovascular_disease"):
                    relevant_flags.update(CVD_FLAGS)
                if cn == "diabetes":
                    relevant_flags.update(DIABETES_FLAGS)
            if relevant_flags:
                st.markdown("**Lifestyle flags**")
                flag_cols = st.columns(2)
                for fi, flag in enumerate(sorted(relevant_flags)):
                    member["lifestyle_flags"][flag] = flag_cols[fi % 2].checkbox(
                        flag.replace("_", " "),
                        value=member["lifestyle_flags"].get(flag, False),
                        key=f"flag_{i}_{flag}",
                    )

            if st.button("🗑 Remove member", key=f"rem_{i}"):
                st.session_state.members.pop(i)
                st.rerun()

    return proband_age, proband_sex, proband_ethnicity, selected_conditions


# ---------------------------------------------------------------------------
# Main — run analysis
# ---------------------------------------------------------------------------

def _build_payload(proband_age, proband_sex, proband_ethnicity, selected_conditions):
    payload = {
        "proband_age": proband_age,
        "proband_sex": proband_sex,
        "conditions_of_interest": selected_conditions,
        "family_members": [
            {
                "name": m["name"],
                "relationship": m["relationship"],
                "sex": m["sex"],
                "is_deceased": m["is_deceased"],
                "conditions": m["conditions"],
                "lifestyle_flags": {k: v for k, v in m["lifestyle_flags"].items() if v},
            }
            for m in st.session_state.members
        ],
    }
    if proband_ethnicity and proband_ethnicity != "not specified":
        payload["proband_ethnicity"] = proband_ethnicity
    return payload


# ---------------------------------------------------------------------------
# Dashboard — charts
# ---------------------------------------------------------------------------

def _render_summary(result: dict):
    summary = result["summary"]
    h = summary["high_priority_count"]
    m = summary["medium_priority_count"]
    lo = summary["low_priority_count"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Alerts", summary["total_alerts"])
    c2.metric("High Priority", h, delta=None)
    c3.metric("Medium Priority", m)
    c4.metric("Low Priority", lo)


def _risk_gauge(title: str, genetic: int, environmental: int, rr: float) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=genetic,
        title={"text": "Genetic", "font": {"size": 13}},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#e63946"},
            "steps": [
                {"range": [0, 33], "color": "#d4edda"},
                {"range": [33, 66], "color": "#fff3cd"},
                {"range": [66, 100], "color": "#f8d7da"},
            ],
        },
        domain={"x": [0, 0.45], "y": [0, 1]},
    ))

    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=environmental,
        title={"text": "Environmental", "font": {"size": 13}},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#f4a261"},
            "steps": [
                {"range": [0, 33], "color": "#d4edda"},
                {"range": [33, 66], "color": "#fff3cd"},
                {"range": [66, 100], "color": "#f8d7da"},
            ],
        },
        domain={"x": [0.55, 1], "y": [0, 1]},
    ))

    fig.update_layout(
        title={"text": f"{title.replace('_', ' ').title()}  |  RR {rr:.2f}×", "x": 0.5},
        height=250,
        margin={"t": 60, "b": 10, "l": 10, "r": 10},
    )
    return fig


def _onset_trend_chart(conditions: dict) -> go.Figure:
    fig = go.Figure()
    has_data = False

    for cond_name, cdata in conditions.items():
        trend = cdata.get("onset_trend", {})
        timeline = trend.get("raw_timeline", [])
        if not timeline:
            continue
        has_data = True
        xs = [p["generation_index"] for p in timeline]
        ys = [p["age_of_onset"] for p in timeline]
        labels = [p["relationship"] for p in timeline]

        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="lines+markers+text",
            name=cond_name.replace("_", " ").title(),
            text=labels,
            textposition="top center",
        ))

        # Trend line
        slope = trend.get("slope")
        intercept = trend.get("intercept")
        if slope is not None and intercept is not None:
            x_range = list(range(min(xs) - 1, 1))
            fig.add_trace(go.Scatter(
                x=x_range,
                y=[intercept + slope * x for x in x_range],
                mode="lines",
                line={"dash": "dot"},
                name=f"{cond_name} trend",
                showlegend=False,
            ))

    gen_labels = {-2: "Grandparents", -1: "Parents", 0: "You", 1: "Children"}
    fig.update_layout(
        title="Age of Onset Across Generations",
        xaxis={
            "title": "Generation",
            "tickvals": [-2, -1, 0, 1],
            "ticktext": [gen_labels[g] for g in [-2, -1, 0, 1]],
        },
        yaxis={"title": "Age of Onset"},
        height=350,
        legend={"orientation": "h"},
    )

    if not has_data:
        fig.add_annotation(
            text="No age-of-onset data available to plot",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font={"size": 14, "color": "gray"},
        )

    return fig


def _genogram(result: dict, members: list) -> go.Figure:
    """Clinical genogram with couple bars, drop lines, and sibship connections."""
    conditions_of_interest = set(result["conditions"].keys())
    high_risk_conditions = {
        a["condition"] for a in result["red_flag_alerts"] if a["priority"] == "high"
    }

    # Fixed (x, y) positions for each named relationship
    REL_POS = {
        "paternal_grandfather": (-2.5, -2), "paternal_grandmother": (-1.5, -2),
        "maternal_grandfather":  (1.5, -2), "maternal_grandmother":  (2.5, -2),
        "grandfather": (-2.5, -2),          "grandmother": (-1.5, -2),
        "great_uncle": (-4.0, -2),          "great_aunt":  (-3.5, -2),
        "father":      (-1.0, -1),          "mother":      (1.0, -1),
        "stepfather":  (-2.0, -1),          "stepmother":  (2.0, -1),
        "paternal_uncle": (-3.0, -1),       "paternal_aunt": (-2.5, -1),
        "maternal_uncle":  (2.5, -1),       "maternal_aunt":  (3.0, -1),
        "uncle": (-3.0, -1),                "aunt": (-2.5, -1),
        "first_cousin": (-3.5, 0),
    }

    SIBLING_RELS = {"brother", "sister", "sibling", "half_brother", "half_sister", "half_sibling"}
    CHILD_RELS   = {"son", "daughter", "child"}

    def _risk(m):
        affected = {c["condition_name"] for c in m.get("conditions", [])} & conditions_of_interest
        if affected & high_risk_conditions:
            return "high", True
        elif affected:
            return "medium", True
        return "none", False

    # Build node registry
    node_map: dict[str, dict] = {}
    sibling_nodes: list[dict] = []
    child_nodes:   list[dict] = []

    node_map["__proband__"] = {
        "x": 0.0, "y": 0.0, "label": "YOU",
        "sex": result["proband_sex"], "risk": "proband",
        "affected": False, "is_deceased": False,
    }

    for m in members:
        rel = m["relationship"]
        risk, affected = _risk(m)
        nd = {
            "label": m.get("name") or rel.replace("_", " "),
            "sex": m.get("sex", "unknown"),
            "risk": risk, "affected": affected,
            "is_deceased": m.get("is_deceased", False),
        }
        if rel in REL_POS:
            nd["x"], nd["y"] = REL_POS[rel]
            node_map[rel] = nd
        elif rel in SIBLING_RELS:
            sibling_nodes.append(nd)
        elif rel in CHILD_RELS:
            child_nodes.append(nd)

    # Spread siblings to the right of proband
    for i, sib in enumerate(sibling_nodes):
        sib["x"] = 1.5 + i * 1.5
        sib["y"] = 0.0
        node_map[f"__sib_{i}__"] = sib

    # Spread children under proband
    n_ch = len(child_nodes)
    for i, ch in enumerate(child_nodes):
        ch["x"] = (i - (n_ch - 1) / 2) * 1.5
        ch["y"] = 1.0
        node_map[f"__child_{i}__"] = ch

    # --- Build figure ---
    fig = go.Figure()
    OFFSET = 0.28   # couple bar height above node centres

    def _line(x0, y0, x1, y1):
        fig.add_shape(
            type="line", x0=x0, y0=y0, x1=x1, y1=y1,
            line={"color": "#999", "width": 1.5}, layer="below",
        )

    def _family_link(p1_key, p2_key, child_keys):
        """Couple bar ➜ drop ➜ sibship ➜ child stubs."""
        p1 = node_map.get(p1_key)
        p2 = node_map.get(p2_key)
        children = [node_map[k] for k in child_keys if k in node_map]
        if not children:
            return

        if p1 and p2:
            bar_y  = p1["y"] + OFFSET
            x_left  = min(p1["x"], p2["x"])
            x_right = max(p1["x"], p2["x"])
            _line(x_left, bar_y, x_right, bar_y)          # couple bar
            _line(p1["x"], p1["y"], p1["x"], bar_y)       # stub p1
            _line(p2["x"], p2["y"], p2["x"], bar_y)       # stub p2
            drop_x   = (p1["x"] + p2["x"]) / 2
            drop_top = bar_y
        elif p1 or p2:
            parent   = p1 or p2
            drop_x   = parent["x"]
            drop_top = parent["y"]
        else:
            return

        child_y   = children[0]["y"]
        sibship_y = child_y + OFFSET
        _line(drop_x, drop_top, drop_x, sibship_y)        # vertical drop

        if len(children) > 1:
            xs = [c["x"] for c in children]
            _line(min(xs), sibship_y, max(xs), sibship_y) # sibship bar

        for ch in children:
            _line(ch["x"], sibship_y, ch["x"], ch["y"])   # child stubs

    # Define which groups are linked
    gen0 = ["__proband__"] + [f"__sib_{i}__" for i in range(len(sibling_nodes))]
    gen1 = [f"__child_{i}__" for i in range(len(child_nodes))]

    _family_link("paternal_grandfather", "paternal_grandmother", ["father"])
    _family_link("grandfather",          "grandmother",          ["father"])
    _family_link("maternal_grandfather", "maternal_grandmother", ["mother"])
    _family_link("father",     "mother",     gen0)
    _family_link("father",     "stepmother", gen0)
    _family_link("stepfather", "mother",     gen0)

    # Single-parent fallbacks (only when no partner is present)
    has_father  = "father"     in node_map or "stepfather" in node_map
    has_mother  = "mother"     in node_map or "stepmother" in node_map
    if has_father and not has_mother:
        _family_link("father" if "father" in node_map else "stepfather", None, gen0)
    if has_mother and not has_father:
        _family_link(None, "mother" if "mother" in node_map else "stepmother", gen0)
    if gen1:
        _family_link("__proband__", None, gen1)

    # --- Draw nodes ---
    RISK_COLOR = {
        "proband": "#1d3557",
        "high":    "#e63946",
        "medium":  "#f4a261",
        "none":    "#a8dadc",
    }
    SEX_SYMBOL = {"male": "square", "female": "circle"}

    xs, ys, colors, symbols, texts, hovers = [], [], [], [], [], []
    for nd in node_map.values():
        xs.append(nd["x"])
        ys.append(nd["y"])
        colors.append(RISK_COLOR.get(nd["risk"], "#a8dadc"))
        symbols.append(SEX_SYMBOL.get(nd.get("sex", ""), "diamond"))
        label = nd["label"] + (" †" if nd.get("is_deceased") else "")
        texts.append(label)
        hovers.append(f"<b>{label}</b><br>Risk: {nd['risk']}")

    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="markers+text",
        marker={
            "symbol": symbols, "color": colors, "size": 30,
            "line": {"color": "white", "width": 2},
        },
        text=texts, textposition="bottom center",
        hovertext=hovers, hoverinfo="text",
    ))

    fig.update_layout(
        title="Family Pedigree (Genogram)",
        yaxis={
            "tickvals": [-2, -1, 0, 1],
            "ticktext": ["Grandparents", "Parents", "You", "Children"],
            "zeroline": False, "range": [-2.8, 1.8],
        },
        xaxis={"visible": False, "range": [-5.5, 5.5]},
        height=520, showlegend=False,
        plot_bgcolor="#f8f9fa",
        margin={"t": 60, "b": 90, "l": 80, "r": 20},
    )

    fig.add_annotation(
        text=(
            "■ Male &nbsp; ● Female &nbsp; ◆ Other &nbsp; † Deceased<br>"
            "<span style='color:#e63946'>■</span> High risk &nbsp;"
            "<span style='color:#f4a261'>■</span> Medium risk &nbsp;"
            "<span style='color:#a8dadc'>■</span> Not affected &nbsp;"
            "<span style='color:#1d3557'>■</span> You"
        ),
        xref="paper", yref="paper", x=0.0, y=-0.20,
        showarrow=False, align="left",
    )
    return fig


def _render_alerts(alerts: list):
    if not alerts:
        st.success("No red flag alerts triggered based on the data entered.")
        return

    for alert in alerts:
        priority = alert["priority"]
        color = PRIORITY_COLOR.get(priority, "#888")
        condition = alert["condition"].replace("_", " ").title()
        st.markdown(
            f"""
            <div style="border-left: 5px solid {color}; padding: 12px 16px;
                        margin-bottom: 10px; background: #fafafa; border-radius: 4px;">
                <strong style="color:{color}; text-transform:uppercase;">{priority}</strong>
                &nbsp;·&nbsp; <strong>{condition}</strong><br/>
                <span style="color:#555;">{alert['trigger_reason']}</span><br/>
                <em style="color:#333;">→ {alert['recommended_action']}</em>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="Gen-Health Analytics",
        page_icon="🧬",
        layout="wide",
    )
    _init_state()

    proband_age, proband_sex, proband_ethnicity, selected_conditions = _render_sidebar()

    st.title("Gen-Health Analytics")
    st.caption("Hereditary Risk & Chronic Disease Predisposition Dashboard")

    if not selected_conditions:
        st.info("Select at least one condition of interest in the sidebar to begin.")
        return

    col_run, _ = st.columns([2, 6])
    if col_run.button("Analyse Family History", type="primary"):
        payload = _build_payload(proband_age, proband_sex, proband_ethnicity, selected_conditions)
        try:
            st.session_state.result = score(payload)
        except ValueError as e:
            st.error(f"Input error: {e}")
            st.session_state.result = None

    result = st.session_state.result

    if result is None:
        st.markdown("### How to use")
        st.markdown(
            """
            1. Enter **your age and biological sex** in the sidebar.
            2. Select the **conditions** you want to analyse (e.g. diabetes, heart disease, breast cancer).
            3. Click **+ Add family member** for each relative you have health information about.
            4. Fill in their relationship, sex, condition, age of onset — then click **+ Add** to save it.
            5. Click **Analyse Family History** to generate your risk dashboard.
            """
        )

        st.divider()
        st.markdown("### What you'll see")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                """
                **Risk Gauges**
                Semicircular meters showing your **Genetic score** and **Environmental score**
                (each 0–100) plus the **Relative Risk Ratio (RR)** vs. the general population.
                Cancer conditions show a rule-based flag card instead.
                """
            )
        with col2:
            st.markdown(
                """
                **Onset Trends**
                A chart plotting the age each relative was diagnosed, across generations.
                A downward slope means the condition is striking earlier each generation —
                a key warning sign.
                """
            )
        with col3:
            st.markdown(
                """
                **Alerts tab**
                Prioritized clinical alerts (High / Medium / Low) with specific recommended
                actions such as genetic counselling or early screening.
                """
            )

        st.divider()
        st.markdown("### Example scenarios to try")

        with st.expander("Scenario 1 — BRCA Cancer Risk (triggers HIGH priority alert)"):
            st.markdown(
                """
                **Your info:** Age `32`, Sex `female`

                **Conditions to select:** `breast_cancer`, `ovarian_cancer`, `diabetes`

                | Member | Relationship | Sex | Condition | Age of Onset |
                |---|---|---|---|---|
                | Patricia | mother | female | breast_cancer | 44 |
                | Susan | maternal_aunt | female | breast_cancer | 48 |
                | Helen | maternal_grandmother | female | ovarian_cancer | 60 |

                **Expected result:**
                - 3 High-priority alerts (BRCA pattern: 2 breast cancer relatives under 50, plus ovarian cancer flag)
                - Breast Cancer card shows **HIGH RISK** with the NCCN trigger reasons
                - Ovarian Cancer card shows **HIGH RISK**
                - Family tree shows red nodes on the maternal side
                """
            )

        with st.expander("Scenario 2 — Early-Onset Heart Disease (CVD trend across generations)"):
            st.markdown(
                """
                **Your info:** Age `38`, Sex `male`

                **Conditions to select:** `heart_disease`, `hypertension`

                | Member | Relationship | Sex | Condition | Age of Onset | Lifestyle flags |
                |---|---|---|---|---|---|
                | James | father | male | heart_disease | 48 | High_BP, Smoking |
                | Robert | paternal_grandfather | male | heart_disease | 55 | — |
                | Michael | paternal_uncle | male | heart_disease | 51 | — |

                **Expected result:**
                - Heart Disease RR ~3.0× (family history multiplier + early-onset penalty)
                - Onset Trends chart shows a **downward slope** — disease appearing earlier each generation
                - High-priority CVD alert with cardiology referral recommendation
                """
            )

        with st.expander("Scenario 3 — Diabetes: Lifestyle vs Genetic split"):
            st.markdown(
                """
                **Your info:** Age `45`, Sex `female`

                **Conditions to select:** `diabetes`, `heart_disease`

                | Member | Relationship | Sex | Condition | Age of Onset | Lifestyle flags |
                |---|---|---|---|---|---|
                | Linda | mother | female | diabetes | 52 | HighBP, HighChol |
                | Dorothy | maternal_grandmother | female | diabetes | 60 | HighBP |
                | Carol | sister | female | diabetes | 40 | HighBP, Smoker |

                **Expected result:**
                - Diabetes RR elevated (~2.3×)
                - **Environmental score higher than Genetic score** — shared lifestyle factors explain
                  most of the risk (all three relatives share High BP)
                - Low-to-medium alert rather than high — lifestyle, not just genetics, is the driver
                """
            )

        st.divider()
        st.markdown("### Key terms")
        terms = {
            "Relative Risk Ratio (RR)": "Your estimated risk compared to the general population. RR 2.0 = twice the average risk. RR 1.0 = no elevation.",
            "Genetic Score (0–100)": "How much of your elevated risk is explained by inherited factors, after removing the lifestyle contribution.",
            "Environmental Score (0–100)": "How much of your elevated risk is explained by shared lifestyle factors (smoking, high BP, obesity, etc.) among affected relatives.",
            "DPF Proxy": "Diabetes Pedigree Function — a hereditary diabetes score based on how many first and second-degree relatives have diabetes. Higher = more hereditary risk.",
            "NCCN Red Flag": "A clinical criterion from the National Comprehensive Cancer Network guidelines. Triggering one means your family pattern matches a known hereditary cancer syndrome.",
            "BRCA1/2": "Genes linked to hereditary breast and ovarian cancer. Flagged when 2+ relatives have breast cancer before age 50, or any relative has ovarian cancer.",
            "First-degree relative": "Parent, sibling, or child — shares approximately 50% of your DNA.",
            "Second-degree relative": "Grandparent, aunt, uncle — shares approximately 25% of your DNA.",
            "Early-onset CVD": "Heart disease before age 55 in a male relative or age 65 in a female relative — a significant hereditary risk marker.",
            "Genogram": "A clinical pedigree diagram showing family structure with health risk colour-coded on each member.",
        }
        for term, definition in terms.items():
            st.markdown(f"**{term}** — {definition}")

        return

    # Summary row
    st.divider()
    _render_summary(result)

    tab_risk, tab_trend, tab_tree, tab_alerts, tab_json = st.tabs(
        ["Risk Gauges", "Onset Trends", "Family Tree", "Alerts", "Raw JSON"]
    )

    with tab_risk:
        conditions = result["conditions"]
        CANCER_CONDITIONS = {
            "breast_cancer", "ovarian_cancer", "male_breast_cancer",
            "colorectal_cancer", "colon_cancer", "rectal_cancer",
        }

        # Separate cancer (rule-based) from numeric conditions
        numeric_conditions = {k: v for k, v in conditions.items() if k not in CANCER_CONDITIONS}
        cancer_conditions = {k: v for k, v in conditions.items() if k in CANCER_CONDITIONS}

        # Numeric gauges (CVD, diabetes, hypertension)
        if numeric_conditions:
            cols = st.columns(min(len(numeric_conditions), 3))
            for idx, (cond_name, cdata) in enumerate(numeric_conditions.items()):
                with cols[idx % len(cols)]:
                    fig = _risk_gauge(
                        cond_name,
                        cdata.get("genetic_predisposition_score", 0),
                        cdata.get("environmental_risk_score", 0),
                        cdata.get("relative_risk_ratio", 1.0),
                    )
                    st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "**Genetic score** (0–100): hereditary contribution to excess risk. "
                "**Environmental score** (0–100): shared lifestyle contribution. "
                "**RR**: relative risk vs. general population."
            )

        # Cancer flag cards (rule-based — no RR model)
        if cancer_conditions:
            if numeric_conditions:
                st.divider()
            st.markdown("#### Cancer Risk (NCCN Rule-Based Assessment)")
            cancer_cols = st.columns(min(len(cancer_conditions), 3))
            for idx, (cond_name, cdata) in enumerate(cancer_conditions.items()):
                with cancer_cols[idx % len(cancer_cols)]:
                    flags = cdata.get("cancer_flags", [])
                    high_flags = [f for f in flags if f.get("priority") == "high"]
                    med_flags  = [f for f in flags if f.get("priority") == "medium"]
                    affected_count = cdata.get("affected_relatives_count", 0)

                    title = cond_name.replace("_", " ").title()
                    if high_flags:
                        border_color = "#e63946"
                        badge = f'<span style="color:#e63946;font-weight:bold;">HIGH RISK</span>'
                        flag_count = len(high_flags)
                    elif med_flags:
                        border_color = "#f4a261"
                        badge = f'<span style="color:#f4a261;font-weight:bold;">MODERATE RISK</span>'
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
                            <span style="color:#aaa;">{affected_count} affected relative(s) entered</span>
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
        st.plotly_chart(
            _onset_trend_chart(result["conditions"]),
            use_container_width=True,
        )
        st.caption(
            "Dotted lines show the OLS trend projected toward your generation. "
            "A negative slope means the condition is appearing earlier each generation."
        )

    with tab_tree:
        st.plotly_chart(
            _genogram(result, st.session_state.members),
            use_container_width=True,
        )

    with tab_alerts:
        _render_alerts(result["red_flag_alerts"])

    with tab_json:
        st.json(result)


if __name__ == "__main__":
    main()
