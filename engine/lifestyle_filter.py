# engine/lifestyle_filter.py
# Use Case 3: Lifestyle vs. Genetics Filtering
# Computes what fraction of observed familial risk is attributable to shared lifestyle factors.

from engine.family_input import FamilyInput, get_members_with_condition
from engine.benchmarks import CVD_LIFESTYLE_RR, DIABETES_LIFESTYLE_RR

# Map condition names to their lifestyle flag set and RR weight table
CONDITION_LIFESTYLE_MAP: dict[str, dict] = {
    "heart_disease": {
        "flags": list(CVD_LIFESTYLE_RR.keys()),
        "rr_table": CVD_LIFESTYLE_RR,
    },
    "cardiovascular_disease": {
        "flags": list(CVD_LIFESTYLE_RR.keys()),
        "rr_table": CVD_LIFESTYLE_RR,
    },
    "diabetes": {
        "flags": list(DIABETES_LIFESTYLE_RR.keys()),
        "rr_table": DIABETES_LIFESTYLE_RR,
    },
}


def _normalize_weight(rr_table: dict) -> dict[str, float]:
    """
    Normalize RR values so they sum to 1 as weights.
    Uses excess RR (RR - 1.0) to weight only the risk contribution, not the baseline.
    """
    excess = {k: max(0.0, v - 1.0) for k, v in rr_table.items()}
    total_excess = sum(excess.values())
    if total_excess == 0:
        n = len(rr_table)
        return {k: 1.0 / n for k in rr_table}
    return {k: e / total_excess for k, e in excess.items()}


def compute_lifestyle_attribution(family_input: FamilyInput, condition: str) -> dict:
    """
    For a given condition, compute the fraction of familial risk explained by shared
    lifestyle factors among affected relatives.

    Returns a dict with:
      - lifestyle_attribution_fraction (0.0–1.0)
      - per_flag breakdown
      - affected_count
    """
    condition_map = CONDITION_LIFESTYLE_MAP.get(condition)
    if condition_map is None:
        # No lifestyle data available for this condition
        return {
            "lifestyle_attribution_fraction": 0.0,
            "per_flag": {},
            "affected_count": 0,
            "note": f"No lifestyle model available for condition '{condition}'",
        }

    affected = get_members_with_condition(family_input, condition)
    if not affected:
        return {
            "lifestyle_attribution_fraction": 0.0,
            "per_flag": {},
            "affected_count": 0,
        }

    flags = condition_map["flags"]
    rr_table = condition_map["rr_table"]
    weights = _normalize_weight(rr_table)

    per_flag = {}
    weighted_attribution = 0.0

    for flag in flags:
        flag_count = sum(1 for m in affected if m.lifestyle_flags.get(flag, False))
        prevalence = flag_count / len(affected)
        weight = weights.get(flag, 0.0)
        contribution = prevalence * weight
        per_flag[flag] = {
            "prevalence_in_affected": round(prevalence, 4),
            "rr_weight": round(weight, 4),
            "contribution": round(contribution, 4),
        }
        weighted_attribution += contribution

    # Clamp to [0, 1]
    attribution = max(0.0, min(1.0, weighted_attribution))

    return {
        "lifestyle_attribution_fraction": round(attribution, 4),
        "per_flag": per_flag,
        "affected_count": len(affected),
    }


def compute_correlation_score(family_input: FamilyInput, condition: str) -> float:
    """
    Returns the lifestyle correlation score as a 0–100 value.
    100 = all affected relatives share all major lifestyle risk factors.
    0   = no shared lifestyle factors among affected relatives.
    """
    result = compute_lifestyle_attribution(family_input, condition)
    return round(result["lifestyle_attribution_fraction"] * 100, 1)


def split_genetic_environmental(
    relative_risk: float, lifestyle_attribution_fraction: float
) -> tuple[int, int]:
    """
    Split the excess risk into genetic and environmental components.

    Formula:
        excess_risk = relative_risk - 1.0
        genetic_excess  = excess_risk * (1 - attribution)
        env_excess      = excess_risk * attribution
        score = min(100, round(component * SCALE_FACTOR))

    SCALE_FACTOR = 25: maps an excess RR of 4.0 (RR=5) to a score of 100.

    Returns: (genetic_predisposition_score, environmental_risk_score) both in [0, 100].
    """
    SCALE_FACTOR = 25.0
    excess = max(0.0, relative_risk - 1.0)
    attribution = max(0.0, min(1.0, lifestyle_attribution_fraction))

    genetic_excess = excess * (1.0 - attribution)
    env_excess = excess * attribution

    genetic_score = min(100, round(genetic_excess * SCALE_FACTOR))
    env_score = min(100, round(env_excess * SCALE_FACTOR))

    return genetic_score, env_score
