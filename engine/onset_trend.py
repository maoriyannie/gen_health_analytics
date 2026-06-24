# engine/onset_trend.py
# Use Case 2: Early-Onset Trend Mapping
# Detects if a condition is appearing at a younger age across generations.

from engine.family_input import FamilyInput, get_members_with_condition


# ---------------------------------------------------------------------------
# Timeline builder
# ---------------------------------------------------------------------------

def build_onset_timeline(family_input: FamilyInput, condition: str) -> list[dict]:
    """
    Build a chronological timeline of age-of-onset across generations for a condition.
    Only includes relatives where age_of_onset is known.
    Returns list sorted by generation_index ascending (oldest generation first).
    """
    affected = get_members_with_condition(family_input, condition)
    timeline = []
    for member in affected:
        for cond in member.conditions:
            if cond.condition_name == condition and cond.age_of_onset is not None:
                timeline.append({
                    "relative_id": member.relative_id,
                    "relationship": member.relationship,
                    "generation_index": member.generation_index,
                    "age_of_onset": cond.age_of_onset,
                    "confirmed": cond.confirmed,
                })
                break  # one entry per relative
    return sorted(timeline, key=lambda x: x["generation_index"])


# ---------------------------------------------------------------------------
# Trend computation (OLS regression)
# ---------------------------------------------------------------------------

def compute_trend(timeline: list[dict]) -> dict:
    """
    Compute generation-over-generation age-of-onset trend via OLS regression.

    Slope interpretation:
      slope < -5  → strongly_accelerating  (5+ years younger per generation)
      slope < -2  → accelerating
     -2 ≤ slope ≤ 2 → stable
      slope > 2  → decelerating

    projected_proband_age: estimated age of onset for the proband (generation_index = 0)
    """
    if len(timeline) < 2:
        return {
            "trend_classification": "insufficient_data",
            "data_points_used": len(timeline),
            "slope": None,
            "intercept": None,
            "generation_delta": None,
            "projected_proband_age": None,
            "raw_timeline": timeline,
        }

    xs = [float(p["generation_index"]) for p in timeline]
    ys = [float(p["age_of_onset"]) for p in timeline]
    n = len(xs)

    x_mean = sum(xs) / n
    y_mean = sum(ys) / n

    numerator = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))
    denominator = sum((xs[i] - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        # All relatives are in the same generation — no trend computable
        return {
            "trend_classification": "insufficient_data",
            "data_points_used": n,
            "slope": None,
            "intercept": None,
            "generation_delta": None,
            "projected_proband_age": None,
            "raw_timeline": timeline,
        }

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean

    # Classify trend
    if slope < -5.0:
        classification = "strongly_accelerating"
    elif slope < -2.0:
        classification = "accelerating"
    elif slope <= 2.0:
        classification = "stable"
    else:
        classification = "decelerating"

    # Project onset age for proband (generation_index = 0)
    projected = intercept + slope * 0.0
    projected = max(0.0, min(120.0, projected))

    return {
        "trend_classification": classification,
        "data_points_used": n,
        "slope": round(slope, 2),
        "intercept": round(intercept, 2),
        "generation_delta": round(slope, 2),  # years younger per generation
        "projected_proband_age": round(projected, 1),
        "raw_timeline": timeline,
    }


# ---------------------------------------------------------------------------
# Analyze all conditions of interest
# ---------------------------------------------------------------------------

def analyze_all_conditions(family_input: FamilyInput) -> dict:
    """
    Run onset trend analysis for every condition in conditions_of_interest.
    Returns a dict keyed by condition name.
    """
    results = {}
    for condition in family_input.conditions_of_interest:
        timeline = build_onset_timeline(family_input, condition)
        results[condition] = compute_trend(timeline)
    return results
