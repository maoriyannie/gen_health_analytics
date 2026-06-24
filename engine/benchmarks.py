# engine/benchmarks.py
# Pre-derived constants from dataset analysis + published clinical guidelines.
# All weights here were computed offline from the datasets and stored as constants
# so the engine runs without re-reading large CSV files at runtime.

# ---------------------------------------------------------------------------
# Population base rates
# Source: diabetes_012_health_indicators_BRFSS2015.csv (253,680 rows)
#         heart_disease_risk_dataset_earlymed.csv (70,000 rows, balanced)
# ---------------------------------------------------------------------------
POPULATION_BASE_RATES = {
    "diabetes": 0.1576,       # 39,967 / 253,680 from BRFSS diabetes_012
    "heart_disease": 0.3021,  # 21,148 / 70,000 rows with Heart_Risk=0 vs Heart_Risk=1
    "cancer": 0.0127,         # SEER US general population (hardcoded from NCI literature)
}

# ---------------------------------------------------------------------------
# Diabetes DPF risk bands
# Source: diabetes.csv — outcome rates computed per DPF quantile band
# DPF (DiabetesPedigreeFunction) range → observed positive outcome rate
# ---------------------------------------------------------------------------
DIABETES_DPF_RISK_BANDS = [
    {"range": (0.000, 0.400), "outcome_rate": 0.292},
    {"range": (0.400, 0.700), "outcome_rate": 0.352},
    {"range": (0.700, 1.000), "outcome_rate": 0.473},
    {"range": (1.000, 1.500), "outcome_rate": 0.610},
    {"range": (1.500, 3.000), "outcome_rate": 0.400},  # small sample, regression toward mean
]

# ---------------------------------------------------------------------------
# CVD lifestyle relative risk weights
# Source: heart_disease_risk_dataset_earlymed.csv
# Computed as: P(Heart_Risk=1 | flag=1) / P(Heart_Risk=1 | flag=0)
# ---------------------------------------------------------------------------
CVD_LIFESTYLE_RR = {
    "Smoking":             1.3956,
    "Obesity":             1.3999,
    "Sedentary_Lifestyle": 1.4018,
    "Chronic_Stress":      1.4019,
    "High_BP":             1.4065,
    "High_Cholesterol":    1.4056,
    "Diabetes":            1.3956,
}

# CVD family history relative risk multiplier
# Source: earlymed — P(Heart_Risk=1|Family_History=1) / P(Heart_Risk=1|Family_History=0)
CVD_FAMILY_HISTORY_RR = 2.316  # 0.6997 / 0.3021

# Early-onset CVD multiplier (per ACC/AHA guidelines)
CVD_EARLY_ONSET_MULTIPLIER = 1.30
CVD_EARLY_ONSET_AGE_MALE = 55
CVD_EARLY_ONSET_AGE_FEMALE = 65

# ---------------------------------------------------------------------------
# Diabetes lifestyle relative risk weights
# Source: diabetes_012_health_indicators_BRFSS2015.csv
# Computed as: P(Diabetes|flag=1) / P(Diabetes|flag=0)
# ---------------------------------------------------------------------------
DIABETES_LIFESTYLE_RR = {
    "HighBP":            1.7211,
    "HighChol":          1.5666,
    "Smoker":            1.1627,
    "PhysInactivity":    1.1897,  # inverse of PhysActivity (protective)
    "HvyAlcoholConsump": 0.4629,  # protective — lower diabetes rate in heavy drinkers
    "Stroke":            2.1783,
    "HeartDiseaseorAttack": 2.2686,
}

# ---------------------------------------------------------------------------
# Clinical thresholds
# Source: AHA, ACC, ADA published guidelines + UCI heart disease dataset
# ---------------------------------------------------------------------------
CLINICAL_THRESHOLDS = {
    "cholesterol_normal":     200,   # mg/dL
    "cholesterol_borderline": 200,
    "cholesterol_high":       240,
    "bp_normal":              120,   # systolic mmHg
    "bp_elevated":            120,
    "bp_stage1":              130,
    "bp_stage2":              140,
    "fasting_glucose_prediabetes": 100,  # mg/dL
    "fasting_glucose_diabetes":    126,
    "early_onset_diabetes_age":    45,
    "early_onset_cvd_age_male":    55,
    "early_onset_cvd_age_female":  65,
    "early_onset_cancer_age":      50,   # general early-onset threshold
}

# ---------------------------------------------------------------------------
# NCCN Cancer Red Flag Rules (rule-based, no dataset required)
# Source: NCCN Clinical Practice Guidelines in Oncology v2.2024
# ---------------------------------------------------------------------------
CANCER_RED_FLAG_RULES = {
    "breast_ovarian": {
        "condition_names": ["breast_cancer", "ovarian_cancer", "male_breast_cancer"],
        "triggers": [
            {
                "condition": "breast_cancer",
                "count_threshold": 2,
                "max_age_of_onset": 50,
                "degree": ["first", "second"],
                "priority": "high",
                "reason": "2+ relatives with breast cancer before age 50 — BRCA1/2 risk",
            },
            {
                "condition": "breast_cancer",
                "count_threshold": 3,
                "max_age_of_onset": None,
                "degree": ["first", "second"],
                "priority": "high",
                "reason": "3+ relatives with breast cancer on same lineage — BRCA1/2 risk",
            },
            {
                "condition": "breast_cancer",
                "count_threshold": 1,
                "max_age_of_onset": 40,
                "degree": ["first"],
                "priority": "high",
                "reason": "First-degree relative with breast cancer before age 40 — BRCA risk",
            },
            {
                "condition": "ovarian_cancer",
                "count_threshold": 1,
                "max_age_of_onset": None,
                "degree": ["first", "second"],
                "priority": "high",
                "reason": "Any ovarian cancer in first/second degree relative — BRCA1/2 risk",
            },
            {
                "condition": "male_breast_cancer",
                "count_threshold": 1,
                "max_age_of_onset": None,
                "degree": ["first", "second"],
                "priority": "high",
                "reason": "Male breast cancer in family — BRCA2 risk",
            },
        ],
    },
    "colorectal": {
        "condition_names": ["colorectal_cancer", "colon_cancer", "rectal_cancer"],
        "triggers": [
            {
                "condition": "colorectal_cancer",
                "count_threshold": 3,
                "max_age_of_onset": None,
                "degree": ["first", "second"],
                "generations_threshold": 2,
                "priority": "high",
                "reason": "3+ relatives with colorectal cancer across 2+ generations — Lynch syndrome risk",
            },
            {
                "condition": "colorectal_cancer",
                "count_threshold": 1,
                "max_age_of_onset": 50,
                "degree": ["first"],
                "priority": "medium",
                "reason": "First-degree relative with colorectal cancer before age 50 — increased risk",
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# Ethnicity-based cancer risk modifiers
# Source: published literature — BRCA1/2 prevalence by ancestry group
# Multipliers applied to NCCN flag count thresholds or alert priority escalation
# ---------------------------------------------------------------------------
# Ashkenazi Jewish BRCA1/2 prevalence: ~1/40 (~2.5%) vs general population ~1/400 (0.25%)
# Source: Struewing et al. NEJM 1997; King et al. Science 2003
ETHNICITY_CANCER_RISK_MODIFIERS = {
    "ashkenazi_jewish": {
        "conditions": ["breast_cancer", "ovarian_cancer", "male_breast_cancer"],
        "brca_multiplier": 10.0,     # 10× higher BRCA1/2 carrier frequency
        "note": "Ashkenazi Jewish ancestry — BRCA1/2 founder mutations (185delAG, 5382insC, 6174delT) confer ~10× higher carrier frequency vs general population",
    },
    "icelandic": {
        "conditions": ["breast_cancer"],
        "brca_multiplier": 4.0,
        "note": "Icelandic ancestry — BRCA2 999del5 founder mutation",
    },
}

# ---------------------------------------------------------------------------
# Relationship to generation index mapping
# Used to infer generation_index when not explicitly provided
# Proband = 0, parents = -1, grandparents = -2, great-grandparents = -3, children = +1
# ---------------------------------------------------------------------------
RELATIONSHIP_TO_GENERATION = {
    # Generation -1 (parents)
    "father":           -1,
    "mother":           -1,
    "stepfather":       -1,
    "stepmother":       -1,
    # Generation -1 (aunts/uncles are siblings of parents)
    "paternal_uncle":   -1,
    "paternal_aunt":    -1,
    "maternal_uncle":   -1,
    "maternal_aunt":    -1,
    "uncle":            -1,
    "aunt":             -1,
    # Generation 0 (proband's generation)
    "sibling":           0,
    "brother":           0,
    "sister":            0,
    "half_sibling":      0,
    "half_brother":      0,
    "half_sister":       0,
    # Generation -2 (grandparents)
    "paternal_grandfather": -2,
    "paternal_grandmother": -2,
    "maternal_grandfather": -2,
    "maternal_grandmother": -2,
    "grandfather":          -2,
    "grandmother":          -2,
    # Generation +1 (children)
    "son":               1,
    "daughter":          1,
    "child":             1,
    # Generation -2 (great-aunts/uncles approximate to grandparent generation)
    "great_uncle":      -2,
    "great_aunt":       -2,
    # First cousin — approximated to parent generation for regression purposes
    "first_cousin":     -1,
    # Generation -3 (great-grandparents)
    "paternal_great_grandfather": -3,
    "paternal_great_grandmother": -3,
    "maternal_great_grandfather": -3,
    "maternal_great_grandmother": -3,
    "great_grandfather":          -3,
    "great_grandmother":          -3,
}

# Degree of relationship classification
FIRST_DEGREE_RELATIONSHIPS = {
    "father", "mother", "sibling", "brother", "sister",
    "son", "daughter", "child", "half_sibling", "half_brother", "half_sister",
}

SECOND_DEGREE_RELATIONSHIPS = {
    "paternal_grandfather", "paternal_grandmother",
    "maternal_grandfather", "maternal_grandmother",
    "grandfather", "grandmother",
    "paternal_uncle", "paternal_aunt",
    "maternal_uncle", "maternal_aunt",
    "uncle", "aunt",
    "first_cousin",
    "great_uncle", "great_aunt",
}

THIRD_DEGREE_RELATIONSHIPS = {
    "paternal_great_grandfather", "paternal_great_grandmother",
    "maternal_great_grandfather", "maternal_great_grandmother",
    "great_grandfather", "great_grandmother",
}

# ---------------------------------------------------------------------------
# Alert recommended actions — keyed by (condition, priority)
# ---------------------------------------------------------------------------
RECOMMENDED_ACTIONS = {
    ("diabetes", "high"):
        "Schedule HbA1c and fasting glucose test immediately. "
        "Discuss family history with your GP. Consider referral to endocrinologist.",
    ("diabetes", "medium"):
        "Request fasting glucose screening at your next check-up. "
        "Focus on lifestyle modifications: weight management and physical activity.",
    ("diabetes", "low"):
        "Monitor glucose annually. Maintain healthy BMI and active lifestyle.",
    ("heart_disease", "high"):
        "Consult a cardiologist. Request lipid panel, ECG, and blood pressure evaluation. "
        "Discuss family history of early-onset CVD with your doctor.",
    ("heart_disease", "medium"):
        "Request cardiovascular risk assessment at your next check-up. "
        "Monitor blood pressure and cholesterol regularly.",
    ("heart_disease", "low"):
        "Maintain heart-healthy lifestyle. Annual BP and cholesterol checks recommended.",
    ("breast_cancer", "high"):
        "Seek genetic counseling for BRCA1/2 testing. "
        "Discuss earlier mammography screening (before age 40) with your doctor. "
        "NCCN guidelines recommend annual MRI for high-risk individuals.",
    ("ovarian_cancer", "high"):
        "Seek genetic counseling for BRCA1/2 testing. "
        "Discuss risk-reducing options with a gynecologic oncologist.",
    ("colorectal_cancer", "high"):
        "Discuss Lynch syndrome genetic testing with your doctor. "
        "Schedule colonoscopy earlier than standard screening age (before age 45).",
    ("colorectal_cancer", "medium"):
        "Request colonoscopy screening starting at age 40 or 10 years before "
        "the earliest age of diagnosis in your family.",
}
