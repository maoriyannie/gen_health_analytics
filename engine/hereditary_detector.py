# engine/hereditary_detector.py
# Use Case 1: Hereditary Red Flag Detection
# Detects elevated hereditary risk for cancer, CVD, and diabetes.

from engine.family_input import (
    FamilyInput,
    get_members_with_condition,
    get_degree,
    estimate_dpf,
)
from engine.benchmarks import (
    CANCER_RED_FLAG_RULES,
    CVD_FAMILY_HISTORY_RR,
    CVD_EARLY_ONSET_MULTIPLIER,
    CVD_EARLY_ONSET_AGE_MALE,
    CVD_EARLY_ONSET_AGE_FEMALE,
    DIABETES_DPF_RISK_BANDS,
    POPULATION_BASE_RATES,
    CLINICAL_THRESHOLDS,
    ETHNICITY_CANCER_RISK_MODIFIERS,
)


# ---------------------------------------------------------------------------
# Cancer — rule-based (NCCN thresholds, no dataset required)
# ---------------------------------------------------------------------------

def detect_cancer_flags(family_input: FamilyInput) -> list[dict]:
    """
    Apply NCCN red flag rules to the family input.
    Ethnicity modifiers (e.g. Ashkenazi Jewish BRCA founder mutations) are appended
    as additional alerts when the proband's ancestry is a known high-risk group.
    """
    triggered = []

    # Ethnicity-based flag (independent of family member count)
    ethnicity = family_input.proband_ethnicity
    if ethnicity and ethnicity in ETHNICITY_CANCER_RISK_MODIFIERS:
        mod = ETHNICITY_CANCER_RISK_MODIFIERS[ethnicity]
        triggered.append({
            "category": "ethnicity",
            "condition": mod["conditions"][0],
            "priority": "high",
            "trigger_reason": mod["note"],
            "matched_relatives_count": 0,
            "matched_relatives": [],
            "ethnicity_modifier": mod["brca_multiplier"],
        })

    for category, ruleset in CANCER_RED_FLAG_RULES.items():
        condition_names = ruleset["condition_names"]

        for trigger in ruleset["triggers"]:
            cond = trigger["condition"]
            # Collect relatives who have this condition
            affected = get_members_with_condition(family_input, cond)

            # Filter by degree
            allowed_degrees = trigger["degree"]
            affected = [m for m in affected if get_degree(m.relationship) in allowed_degrees]

            # Filter by max age of onset if specified
            max_age = trigger.get("max_age_of_onset")
            if max_age is not None:
                affected = [
                    m for m in affected
                    if any(
                        c.condition_name == cond and c.age_of_onset is not None
                        and c.age_of_onset <= max_age
                        for c in m.conditions
                    )
                ]

            # Filter by generations threshold if specified (Lynch syndrome)
            gen_threshold = trigger.get("generations_threshold")
            if gen_threshold is not None:
                generations_represented = len({m.generation_index for m in affected})
                if generations_represented < gen_threshold:
                    continue

            count = len(affected)
            if count >= trigger["count_threshold"]:
                triggered.append({
                    "category": category,
                    "condition": cond,
                    "priority": trigger["priority"],
                    "trigger_reason": trigger["reason"],
                    "matched_relatives_count": count,
                    "matched_relatives": [m.relative_id for m in affected],
                })

    return triggered


# ---------------------------------------------------------------------------
# CVD — data-driven (earlymed dataset benchmarks)
# ---------------------------------------------------------------------------

def detect_cvd_risk(family_input: FamilyInput) -> dict:
    """
    Compute CVD hereditary risk from family history.
    Uses pre-derived relative risk ratio from earlymed dataset.
    """
    cvd_conditions = ["heart_disease", "cardiovascular_disease", "coronary_artery_disease"]
    affected = []
    for cond in cvd_conditions:
        affected.extend(get_members_with_condition(family_input, cond))

    # Deduplicate by relative_id
    seen = set()
    unique_affected = []
    for m in affected:
        if m.relative_id not in seen:
            seen.add(m.relative_id)
            unique_affected.append(m)

    family_history_flag = len(unique_affected) > 0
    relative_risk = CVD_FAMILY_HISTORY_RR if family_history_flag else 1.0

    # Early-onset penalty: any affected relative onset before age threshold
    early_onset_flag = False
    for member in unique_affected:
        for cond in member.conditions:
            if cond.condition_name in cvd_conditions and cond.age_of_onset is not None:
                threshold = (
                    CVD_EARLY_ONSET_AGE_MALE
                    if member.sex == "male"
                    else CVD_EARLY_ONSET_AGE_FEMALE
                )
                if cond.age_of_onset <= threshold:
                    early_onset_flag = True
                    break

    if early_onset_flag:
        relative_risk *= CVD_EARLY_ONSET_MULTIPLIER

    return {
        "condition": "heart_disease",
        "relative_risk_ratio": round(relative_risk, 4),
        "family_history_flag": family_history_flag,
        "early_onset_flag": early_onset_flag,
        "affected_relatives_count": len(unique_affected),
        "affected_relative_ids": [m.relative_id for m in unique_affected],
        "population_base_rate": POPULATION_BASE_RATES["heart_disease"],
    }


# ---------------------------------------------------------------------------
# Diabetes — data-driven (DPF proxy + risk bands)
# ---------------------------------------------------------------------------

def _lookup_dpf_band(dpf: float) -> dict:
    """Look up the DPF risk band for a given DPF value."""
    for band in DIABETES_DPF_RISK_BANDS:
        lo, hi = band["range"]
        if lo <= dpf < hi:
            return band
    # Clamp to last band if out of range
    return DIABETES_DPF_RISK_BANDS[-1]


def detect_diabetes_risk(family_input: FamilyInput) -> dict:
    """
    Compute diabetes hereditary risk using a DPF proxy derived from family history.
    """
    affected = get_members_with_condition(family_input, "diabetes")
    dpf_proxy = estimate_dpf(family_input)
    band = _lookup_dpf_band(dpf_proxy)
    outcome_rate = band["outcome_rate"]
    base_rate = POPULATION_BASE_RATES["diabetes"]
    relative_risk = outcome_rate / base_rate

    return {
        "condition": "diabetes",
        "relative_risk_ratio": round(relative_risk, 4),
        "dpf_proxy": round(dpf_proxy, 4),
        "outcome_rate": outcome_rate,
        "risk_band": f"[{band['range'][0]}-{band['range'][1]})",
        "affected_relatives_count": len(affected),
        "affected_relative_ids": [m.relative_id for m in affected],
        "population_base_rate": base_rate,
    }
