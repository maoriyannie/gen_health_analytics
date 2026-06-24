# engine/family_input.py
# Input validation, data structures, and helper functions for family health records.

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from engine.benchmarks import (
    RELATIONSHIP_TO_GENERATION,
    FIRST_DEGREE_RELATIONSHIPS,
    SECOND_DEGREE_RELATIONSHIPS,
    THIRD_DEGREE_RELATIONSHIPS,
)

VALID_RELATIONSHIPS = set(RELATIONSHIP_TO_GENERATION.keys())

VALID_SEXES = {"male", "female", "other", "unknown"}

# Conditions the engine knows how to score
SUPPORTED_CONDITIONS = {
    "diabetes",
    "heart_disease",
    "breast_cancer",
    "ovarian_cancer",
    "male_breast_cancer",
    "colorectal_cancer",
    "colon_cancer",
    "rectal_cancer",
    "hypertension",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ConditionRecord:
    condition_name: str           # normalized to lowercase_snake_case
    age_of_onset: Optional[int]   # None if unknown
    confirmed: bool = True        # False = family report, not clinically confirmed
    cause_of_death: bool = False  # True if this condition was cause of death


@dataclass
class FamilyMember:
    relative_id: str
    relationship: str             # e.g. "father", "maternal_grandmother"
    generation_index: int         # 0=proband, -1=parents, -2=grandparents, +1=children
    sex: str                      # "male" | "female" | "other" | "unknown"
    is_deceased: bool
    conditions: list[ConditionRecord] = field(default_factory=list)
    lifestyle_flags: dict[str, bool] = field(default_factory=dict)
    name: str = ""


@dataclass
class FamilyInput:
    proband_age: int
    proband_sex: str
    conditions_of_interest: list[str]
    family_members: list[FamilyMember]
    proband_ethnicity: Optional[str] = None   # e.g. "ashkenazi_jewish", "icelandic"


# ---------------------------------------------------------------------------
# Parsing and validation
# ---------------------------------------------------------------------------

def _normalize_condition(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def _normalize_relationship(rel: str) -> str:
    return rel.strip().lower().replace(" ", "_").replace("-", "_")


def _infer_generation(relationship: str) -> int:
    gen = RELATIONSHIP_TO_GENERATION.get(relationship)
    if gen is None:
        raise ValueError(
            f"Unknown relationship '{relationship}'. "
            f"Valid values: {sorted(VALID_RELATIONSHIPS)}"
        )
    return gen


def validate_and_parse(raw: dict) -> FamilyInput:
    """
    Parse and validate a raw family input dict into a FamilyInput object.
    Raises ValueError with a descriptive message on invalid input.
    """
    if not isinstance(raw, dict):
        raise ValueError("Input must be a JSON object (dict).")

    # Proband fields
    proband_age = raw.get("proband_age")
    if proband_age is None or not isinstance(proband_age, (int, float)) or proband_age <= 0:
        raise ValueError("'proband_age' must be a positive integer.")
    proband_age = int(proband_age)

    proband_sex = str(raw.get("proband_sex", "unknown")).lower()
    if proband_sex not in VALID_SEXES:
        raise ValueError(f"'proband_sex' must be one of {VALID_SEXES}.")

    # Conditions of interest
    raw_conditions = raw.get("conditions_of_interest", [])
    if not isinstance(raw_conditions, list) or len(raw_conditions) == 0:
        raise ValueError("'conditions_of_interest' must be a non-empty list of condition names.")
    conditions_of_interest = [_normalize_condition(c) for c in raw_conditions]

    # Family members
    raw_members = raw.get("family_members", [])
    if not isinstance(raw_members, list):
        raise ValueError("'family_members' must be a list.")

    members: list[FamilyMember] = []
    for i, m in enumerate(raw_members):
        if not isinstance(m, dict):
            raise ValueError(f"family_members[{i}] must be an object.")

        relative_id = str(m.get("relative_id", f"R{i:03d}"))
        name = str(m.get("name", ""))

        relationship = _normalize_relationship(str(m.get("relationship", "")))
        if not relationship:
            raise ValueError(f"family_members[{i}] missing 'relationship'.")

        # generation_index: use provided value or infer from relationship
        if "generation_index" in m:
            try:
                generation_index = int(m["generation_index"])
            except (ValueError, TypeError):
                raise ValueError(
                    f"family_members[{i}].generation_index must be an integer."
                )
        else:
            generation_index = _infer_generation(relationship)

        sex = str(m.get("sex", "unknown")).lower()
        if sex not in VALID_SEXES:
            sex = "unknown"

        is_deceased = bool(m.get("is_deceased", False))

        # Conditions
        conditions: list[ConditionRecord] = []
        for j, c in enumerate(m.get("conditions", [])):
            if not isinstance(c, dict):
                raise ValueError(
                    f"family_members[{i}].conditions[{j}] must be an object."
                )
            cname = _normalize_condition(str(c.get("condition_name", "")))
            if not cname:
                raise ValueError(
                    f"family_members[{i}].conditions[{j}] missing 'condition_name'."
                )
            aoo = c.get("age_of_onset")
            if aoo is not None:
                try:
                    aoo = int(aoo)
                except (ValueError, TypeError):
                    aoo = None
            conditions.append(
                ConditionRecord(
                    condition_name=cname,
                    age_of_onset=aoo,
                    confirmed=bool(c.get("confirmed", True)),
                    cause_of_death=bool(c.get("cause_of_death", False)),
                )
            )

        # Lifestyle flags — normalize keys to match benchmarks column names
        lifestyle_flags: dict[str, bool] = {
            k: bool(v) for k, v in m.get("lifestyle_flags", {}).items()
        }

        members.append(
            FamilyMember(
                relative_id=relative_id,
                name=name,
                relationship=relationship,
                generation_index=generation_index,
                sex=sex,
                is_deceased=is_deceased,
                conditions=conditions,
                lifestyle_flags=lifestyle_flags,
            )
        )

    # Ethnicity (optional)
    raw_ethnicity = raw.get("proband_ethnicity")
    proband_ethnicity = str(raw_ethnicity).strip().lower().replace(" ", "_") if raw_ethnicity else None

    return FamilyInput(
        proband_age=proband_age,
        proband_sex=proband_sex,
        conditions_of_interest=conditions_of_interest,
        family_members=members,
        proband_ethnicity=proband_ethnicity,
    )


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def get_members_with_condition(
    family_input: FamilyInput, condition: str
) -> list[FamilyMember]:
    """Return members who have the given condition, sorted by generation_index ascending."""
    condition = _normalize_condition(condition)
    result = [
        m for m in family_input.family_members
        if any(c.condition_name == condition for c in m.conditions)
    ]
    return sorted(result, key=lambda m: m.generation_index)


def get_degree(relationship: str) -> str:
    """Return 'first', 'second', 'third', or 'other' degree for a relationship string."""
    rel = _normalize_relationship(relationship)
    if rel in FIRST_DEGREE_RELATIONSHIPS:
        return "first"
    if rel in SECOND_DEGREE_RELATIONSHIPS:
        return "second"
    if rel in THIRD_DEGREE_RELATIONSHIPS:
        return "third"
    return "other"


# ---------------------------------------------------------------------------
# DPF proxy estimation
# ---------------------------------------------------------------------------

def estimate_dpf(family_input: FamilyInput) -> float:
    """
    Estimate a DiabetesPedigreeFunction (DPF) proxy from family history of diabetes.

    Formula: clamp(0.20 + weighted_count * 0.15,  min=0.078, max=2.42)
    - First-degree relatives with diabetes: weight 1.0 each
    - Second-degree relatives with diabetes: weight 0.5 each

    Calibration: 0 relatives → DPF ≈ 0.20 (below dataset mean 0.47 for non-diabetic)
                 1 first-degree → DPF ≈ 0.35
                 2 first-degree → DPF ≈ 0.50 (near dataset mean for diabetic group)
                 3+ first-degree → DPF > 0.65 (elevated band)

    Note: This is a heuristic approximation. The original DPF is a lab-derived
    score from the Pima Indian cohort. This proxy enables risk banding from
    qualitative family input only.
    """
    weighted_count = 0.0
    for member in family_input.family_members:
        has_diabetes = any(c.condition_name == "diabetes" for c in member.conditions)
        if not has_diabetes:
            continue
        degree = get_degree(member.relationship)
        if degree == "first":
            weighted_count += 1.0
        elif degree == "second":
            weighted_count += 0.5
        elif degree == "third":
            weighted_count += 0.25

    dpf_proxy = 0.20 + weighted_count * 0.15
    return max(0.078, min(2.42, dpf_proxy))
