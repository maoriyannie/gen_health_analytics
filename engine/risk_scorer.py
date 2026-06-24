# engine/risk_scorer.py
# Orchestrator: calls all sub-engines and assembles the final output dict.

from datetime import datetime, timezone

from engine.family_input import validate_and_parse, FamilyInput, get_members_with_condition
from engine.hereditary_detector import detect_cancer_flags, detect_cvd_risk, detect_diabetes_risk
from engine.onset_trend import analyze_all_conditions
from engine.lifestyle_filter import (
    compute_lifestyle_attribution,
    compute_correlation_score,
    split_genetic_environmental,
)
from engine.alert_builder import build_alerts

ANALYSIS_VERSION = "1.0.0"

# Conditions routed to each detector
CANCER_CONDITIONS = {
    "breast_cancer", "ovarian_cancer", "male_breast_cancer",
    "colorectal_cancer", "colon_cancer", "rectal_cancer",
}
CVD_CONDITIONS = {"heart_disease", "cardiovascular_disease", "coronary_artery_disease"}
DIABETES_CONDITIONS = {"diabetes"}


def score(raw_family_dict: dict) -> dict:
    """
    Main entry point. Accepts a raw family input dict, runs all analytics,
    and returns the unified result dict.
    """
    family_input: FamilyInput = validate_and_parse(raw_family_dict)

    # Run onset trend analysis for all conditions of interest
    onset_trends = analyze_all_conditions(family_input)

    # Run cancer red flag detection once (covers all cancer conditions)
    cancer_flags = detect_cancer_flags(family_input)
    # Group cancer flags by condition for easy lookup
    cancer_flags_by_condition: dict[str, list] = {}
    for flag in cancer_flags:
        cancer_flags_by_condition.setdefault(flag["condition"], []).append(flag)

    # Score each condition
    scored_conditions: dict[str, dict] = {}

    for condition in family_input.conditions_of_interest:
        result: dict = {"condition": condition}

        # --- Hereditary detection ---
        if condition in CVD_CONDITIONS:
            detection = detect_cvd_risk(family_input)
        elif condition in DIABETES_CONDITIONS:
            detection = detect_diabetes_risk(family_input)
        elif condition in CANCER_CONDITIONS:
            # Cancer uses rule-based flags — no numeric RR from detector
            affected = get_members_with_condition(family_input, condition)
            detection = {
                "condition": condition,
                "relative_risk_ratio": 1.0,
                "affected_relatives_count": len(affected),
                "affected_relative_ids": [m.relative_id for m in affected],
                "population_base_rate": 0.0127,
            }
        else:
            # Unknown condition — return baseline
            detection = {
                "condition": condition,
                "relative_risk_ratio": 1.0,
                "affected_relatives_count": 0,
                "affected_relative_ids": [],
            }

        result.update(detection)

        # Attach cancer flags for this condition
        result["cancer_flags"] = cancer_flags_by_condition.get(condition, [])

        # --- Lifestyle attribution ---
        lifestyle = compute_lifestyle_attribution(family_input, condition)
        result["lifestyle_attribution"] = lifestyle
        result["correlation_score"] = compute_correlation_score(family_input, condition)

        rr = result.get("relative_risk_ratio", 1.0)
        attribution_fraction = lifestyle["lifestyle_attribution_fraction"]
        genetic_score, env_score = split_genetic_environmental(rr, attribution_fraction)
        result["genetic_predisposition_score"] = genetic_score
        result["environmental_risk_score"] = env_score

        # --- Onset trend ---
        result["onset_trend"] = onset_trends.get(condition, {"trend_classification": "insufficient_data"})

        scored_conditions[condition] = result

    # Build alerts
    alerts = build_alerts(scored_conditions)

    # Summary
    priority_counts = {"high": 0, "medium": 0, "low": 0}
    for alert in alerts:
        p = alert.get("priority", "low")
        priority_counts[p] = priority_counts.get(p, 0) + 1

    top_genetic = max(
        (v.get("genetic_predisposition_score", 0) for v in scored_conditions.values()), default=0
    )
    top_env = max(
        (v.get("environmental_risk_score", 0) for v in scored_conditions.values()), default=0
    )
    highest_rr_condition = max(
        scored_conditions, key=lambda c: scored_conditions[c].get("relative_risk_ratio", 1.0),
        default=None,
    )

    return {
        "analysis_version": ANALYSIS_VERSION,
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "proband_age": family_input.proband_age,
        "proband_sex": family_input.proband_sex,
        "conditions": scored_conditions,
        "red_flag_alerts": alerts,
        "summary": {
            "highest_priority_condition": highest_rr_condition,
            "total_alerts": len(alerts),
            "high_priority_count": priority_counts["high"],
            "medium_priority_count": priority_counts["medium"],
            "low_priority_count": priority_counts["low"],
            "top_genetic_score": top_genetic,
            "top_environmental_score": top_env,
        },
    }
