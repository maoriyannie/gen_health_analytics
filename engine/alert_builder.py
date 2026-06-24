# engine/alert_builder.py
# Translates scored results into structured, prioritized alerts.

import uuid
from engine.benchmarks import RECOMMENDED_ACTIONS


def _get_recommended_action(condition: str, priority: str) -> str:
    action = RECOMMENDED_ACTIONS.get((condition, priority))
    if action:
        return action
    # Fallback for conditions not in the table
    return (
        f"Discuss your family history of {condition.replace('_', ' ')} "
        f"with your healthcare provider."
    )


def build_alerts(scored_conditions: dict) -> list[dict]:
    """
    Generate prioritized alerts from the scored condition results.

    Priority rules (first match wins per condition):
      1. Cancer red flags (already have priority from hereditary_detector)
      2. RR >= 3.0              → high
      3. strongly_accelerating  → high
      4. RR >= 2.0              → medium
      5. accelerating trend     → medium
      6. DPF proxy >= 1.0       → high
      7. DPF proxy >= 0.7       → medium
      8. early_onset_flag CVD   → high
      9. RR >= 1.5              → low
    """
    alerts = []

    for condition, result in scored_conditions.items():
        # Cancer conditions come with flags already set by hereditary_detector
        cancer_flags = result.get("cancer_flags", [])
        for flag in cancer_flags:
            alerts.append({
                "alert_id": str(uuid.uuid4()),
                "condition": flag["condition"],
                "priority": flag["priority"],
                "trigger_reason": flag["trigger_reason"],
                "genetic_predisposition_score": result.get("genetic_predisposition_score", 0),
                "environmental_risk_score": result.get("environmental_risk_score", 0),
                "recommended_action": _get_recommended_action(flag["condition"], flag["priority"]),
            })

        rr = result.get("relative_risk_ratio", 1.0)
        trend = result.get("onset_trend", {}).get("trend_classification", "insufficient_data")
        dpf = result.get("dpf_proxy")
        early_onset = result.get("early_onset_flag", False)
        genetic_score = result.get("genetic_predisposition_score", 0)
        env_score = result.get("environmental_risk_score", 0)

        priority = None
        reason_parts = []

        # Rule 1: RR >= 3.0 → high
        if rr >= 3.0:
            priority = "high"
            reason_parts.append(f"Relative risk ratio {rr:.2f} exceeds high-risk threshold of 3.0")

        # Rule 2: strongly accelerating trend → high
        if trend == "strongly_accelerating":
            priority = "high"
            slope = result.get("onset_trend", {}).get("slope")
            reason_parts.append(
                f"Strongly accelerating onset trend ({abs(slope):.1f} years younger per generation)"
                if slope is not None else "Strongly accelerating onset trend detected"
            )

        # Rule 3: RR >= 2.0 → medium (if not already high)
        if priority is None and rr >= 2.0:
            priority = "medium"
            reason_parts.append(f"Relative risk ratio {rr:.2f} exceeds moderate-risk threshold of 2.0")

        # Rule 4: accelerating trend → medium
        if priority is None and trend == "accelerating":
            priority = "medium"
            slope = result.get("onset_trend", {}).get("slope")
            reason_parts.append(
                f"Accelerating onset trend ({abs(slope):.1f} years younger per generation)"
                if slope is not None else "Accelerating onset trend detected"
            )

        # Rule 5: DPF proxy >= 1.0 → high (diabetes-specific)
        if dpf is not None and dpf >= 1.0:
            priority = "high"
            reason_parts.append(f"Estimated hereditary diabetes score (DPF proxy) {dpf:.2f} ≥ 1.0")

        # Rule 6: DPF proxy >= 0.7 → medium (diabetes-specific)
        if priority is None and dpf is not None and dpf >= 0.7:
            priority = "medium"
            reason_parts.append(f"Estimated hereditary diabetes score (DPF proxy) {dpf:.2f} ≥ 0.7")

        # Rule 7: early onset CVD → high
        if early_onset and condition in ("heart_disease", "cardiovascular_disease"):
            priority = "high"
            reason_parts.append("Family history includes early-onset cardiovascular disease")

        # Rule 8: RR >= 1.5 → low (if no higher rule matched)
        if priority is None and rr >= 1.5:
            priority = "low"
            reason_parts.append(f"Relative risk ratio {rr:.2f} is mildly elevated above baseline")

        # Only emit an alert if a rule was triggered
        if priority is not None and reason_parts:
            alerts.append({
                "alert_id": str(uuid.uuid4()),
                "condition": condition,
                "priority": priority,
                "trigger_reason": ". ".join(reason_parts) + ".",
                "genetic_predisposition_score": genetic_score,
                "environmental_risk_score": env_score,
                "recommended_action": _get_recommended_action(condition, priority),
            })

    # Sort: high first, then medium, then low
    priority_order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: priority_order.get(a["priority"], 3))

    return alerts
