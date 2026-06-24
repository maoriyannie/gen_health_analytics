# Gen-Health Analytics
### A Digital Dashboard for Visualizing Hereditary Risk and Chronic Disease Predisposition

Gen-Health Analytics is a preventive health informatics tool that bridges the gap between genealogical research and clinical risk assessment. It structures multi-generational family medical data to identify hereditary risk patterns for cardiovascular disease, type 2 diabetes, and cancers — helping you understand whether conditions in your family are driven by genetics, shared lifestyle, or both.

---

## Getting Started

### Prerequisites

- Python 3.9+
- pipenv (recommended) or pip

### Installation

```bash
pipenv install
# or
pip install -r requirements.txt
```

### Running the Dashboard

```bash
pipenv run streamlit run app.py
```

Opens at `http://localhost:8501` in your browser.

### Running the Engine via CLI

```bash
# Run with a JSON input file
python main.py my_family.json

# Run with stdin
cat my_family.json | python main.py
```

Output is JSON written to stdout. See `schemas/input_schema.json` and `schemas/output_schema.json` for the full data contracts.

---

## How This Project Addresses the Assessment Criteria

This section maps each criterion from the assessment rubric to what was implemented and how.

### 1. Data Collection and Structure

| Criterion | Implementation |
|---|---|
| **Three-generation depth** | The engine supports four generations: great-grandparents (generation −3), grandparents (−2), parents and aunts/uncles (−1), the proband (0), and children (+1). Great-grandparent relationships (`paternal_great_grandfather`, `maternal_great_grandmother`, etc.) are fully supported in the input schema and inferred automatically from the relationship string. |
| **Key health milestones** | Each family member stores conditions (diagnosis), age of onset, whether the condition was clinically confirmed, and whether it was the cause of death. |
| **Age of onset** | Required per condition. Used directly in NCCN red-flag rules (e.g. breast cancer before age 50) and in OLS onset trend regression across generations. |
| **Cause of death** | Captured per condition. Accepts a boolean (`true`/`false`) or a descriptive string (e.g. `"myocardial infarction"`). |
| **Lifestyle factors** | Per-member lifestyle flags drive the lifestyle attribution model, which separates shared environmental risk from inherited genetic risk. CVD flags: Smoking, Obesity, Sedentary\_Lifestyle, High\_BP, High\_Cholesterol, Chronic\_Stress, Diabetes. Diabetes flags: HighBP, HighChol, Smoker, PhysInactivity, HvyAlcoholConsump. |
| **Ethnicity / ancestry** | A `proband_ethnicity` field applies ancestry-specific risk modifiers. Ashkenazi Jewish ancestry triggers a high-priority BRCA alert based on the ~10× higher carrier frequency of BRCA1/2 founder mutations in that population (Struewing et al., NEJM 1997; King et al., Science 2003). |

---

### 2. Analysis and Interpretation Techniques

#### Pedigree Visualization

The dashboard renders an interactive genogram (clinical pedigree diagram) using Plotly. Each relative is represented as a shape (square = male, circle = female, diamond = other) colour-coded by risk level: red (high), orange (medium), teal (affected but no elevated risk), dark blue (proband). A † symbol marks deceased relatives. Lines show family structure — couple bars connect parents, drop lines connect to children.

#### Red Flag Identification

Two red-flag mechanisms run in parallel:

1. **NCCN rule-based cancer flags** — Encodes the same criteria applied by genetic counsellors under NCCN Clinical Practice Guidelines v2.2024. Checks for: 2+ relatives with breast cancer before age 50 (BRCA1/2), 3+ relatives with breast cancer on the same lineage, any ovarian cancer (BRCA1/2), male breast cancer (BRCA2), 3+ relatives with colorectal cancer across 2+ generations (Lynch syndrome), and first-degree colorectal cancer before age 50.
2. **Ethnicity-based flags** — Applied independently of family member count. Ashkenazi Jewish and Icelandic ancestries trigger additional BRCA alerts referencing the specific founder mutations involved.

#### Risk Estimation

For diabetes and heart disease, the engine computes a Relative Risk Ratio (RR) — the ratio of the proband's estimated disease probability to the population base rate. An RR of 2.0 means twice the average population risk.

#### Onset Trend Analysis

OLS (Ordinary Least Squares) regression is applied across `(generation_index, age_of_onset)` data points. The slope of the regression line indicates whether a condition is appearing at progressively younger ages each generation. Classified as: `strongly_accelerating` (slope < −5), `accelerating` (slope < −2), `stable`, or `decelerating`. Requires data from at least two different generations.

#### Ethnicity / Ancestry Analysis

The `proband_ethnicity` field routes known high-risk ancestries to ethnicity-specific alert rules. Currently supported:
- **Ashkenazi Jewish** — BRCA1/2 founder mutations (185delAG, 5382insC, 6174delT), ~10× higher carrier frequency vs general population
- **Icelandic** — BRCA2 999del5 founder mutation, ~4× higher carrier frequency

---

### 3. Actionable Outcomes

| Outcome Type | Implementation |
|---|---|
| **Proactive screening** | Every alert includes a recommended action — a specific clinical step (e.g. "request HbA1c and fasting glucose", "schedule colonoscopy before age 45", "annual MRI for BRCA high-risk individuals"). |
| **Lifestyle customisation** | The lifestyle attribution model computes what fraction of familial risk is explained by shared lifestyle flags vs inherited factors. The Environmental Risk Score (0–100) vs Genetic Predisposition Score (0–100) helps users understand whether diet and exercise changes are the highest-leverage intervention. |
| **Genetic counselling referrals** | NCCN and ethnicity-triggered alerts explicitly recommend "seek genetic counselling for BRCA1/2 testing" or "discuss Lynch syndrome genetic testing with your doctor." These are the same referral thresholds used in hospital genetics clinics. |

---

### 4. Best Practices and Limitations

**Standardisation:** All condition names are normalised to `lowercase_snake_case` on input. Relationship strings are normalised and mapped to a canonical generation index. Numeric constants are stored centrally in `engine/benchmarks.py` with source citations.

**Verification:** The tool accepts a `confirmed` boolean per condition (default `true`) to distinguish between clinically confirmed diagnoses and family-reported history. Unconfirmed conditions still contribute to scoring but can be filtered downstream.

**Privacy:** No external API calls are made. The engine runs entirely offline. No family data is transmitted or stored outside the user's machine.

**Limitations:** Gen-Health Analytics is a screening tool, not a diagnostic device. Risk scores are population-level estimates — they indicate elevated probability compared to average, not certainty of disease. Outputs are intended to support, not replace, clinical evaluation by a qualified healthcare professional.

---

## How the Answers Are Derived — Formulas and Benchmarks

This section answers the assessment question: *"How to get the answers, what formula or way used, what benchmark is used?"*

### Diabetes Risk

**Formula — DPF Proxy (Diabetes Pedigree Function):**

```
DPF_proxy = clamp(0.20 + (n_first × 1.0 + n_second × 0.5 + n_third × 0.25) × 0.15,
            min=0.078, max=2.42)
```

Where `n_first`, `n_second`, `n_third` are the counts of first-, second-, and third-degree relatives with diabetes. First-degree relatives (parents, siblings, children) share ~50% of DNA and contribute the most weight; third-degree (great-grandparents) contribute least.

**Formula — Relative Risk Ratio (RR):**

```
RR = outcome_rate_in_DPF_band / population_base_rate
```

**Benchmark — DPF risk bands:**  
Source: `diabetes.csv` (Pima Indians diabetes dataset). Outcome rates were computed per DPF quantile band:

| DPF Range | Observed Outcome Rate |
|---|---|
| 0.000 – 0.400 | 29.2% |
| 0.400 – 0.700 | 35.2% |
| 0.700 – 1.000 | 47.3% |
| 1.000 – 1.500 | 61.0% |
| 1.500 – 3.000 | 40.0% (small sample, regression toward mean) |

**Benchmark — Population base rate for diabetes:**  
Source: `diabetes_012_health_indicators_BRFSS2015.csv` (253,680 respondents, BRFSS 2015 survey).  
Base rate = 39,967 / 253,680 = **15.76%**

**Benchmark — Lifestyle relative risk weights for diabetes:**  
Source: BRFSS 2015. Computed as P(Diabetes | flag = 1) / P(Diabetes | flag = 0):

| Lifestyle Flag | Relative Risk Weight |
|---|---|
| High Blood Pressure | 1.7211 |
| High Cholesterol | 1.5666 |
| Stroke history | 2.1783 |
| Heart Disease / Attack | 2.2686 |
| Physical Inactivity | 1.1897 |
| Smoking | 1.1627 |
| Heavy Alcohol | 0.4629 (protective) |

---

### Heart Disease (CVD) Risk

**Formula — Family History RR:**

```
RR = CVD_FAMILY_HISTORY_RR                        (if any relative has CVD)
   × CVD_EARLY_ONSET_MULTIPLIER                   (if any affected relative was early-onset)
```

Where `CVD_EARLY_ONSET_MULTIPLIER = 1.30` and early onset is defined as diagnosis before age 55 (male) or 65 (female), per AHA/ACC guidelines.

**Benchmark — CVD family history multiplier:**  
Source: `heart_disease_risk_dataset_earlymed.csv` (70,000 rows, EarlyMed dataset).  
Computed as P(Heart\_Risk=1 | Family\_History=1) / P(Heart\_Risk=1 | Family\_History=0) = 0.6997 / 0.3021 = **2.316**

**Benchmark — Population base rate for CVD:**  
Source: EarlyMed dataset.  
Base rate = 21,148 / 70,000 = **30.21%**

**Benchmark — CVD lifestyle relative risk weights:**  
Source: EarlyMed dataset. Computed as P(Heart\_Risk=1 | flag=1) / P(Heart\_Risk=1 | flag=0):

| Lifestyle Flag | Relative Risk Weight |
|---|---|
| High BP | 1.4065 |
| High Cholesterol | 1.4056 |
| Chronic Stress | 1.4019 |
| Sedentary Lifestyle | 1.4018 |
| Obesity | 1.3999 |
| Smoking | 1.3956 |
| Diabetes | 1.3956 |

---

### Cancer Risk

**Formula — NCCN Rule Evaluation:**  
No population RR is computed for cancer. Instead, the engine evaluates a structured rule set derived from NCCN Clinical Practice Guidelines in Oncology v2.2024 — the same criteria applied in hospital genetics clinics.

Each rule has:
- A condition name (breast\_cancer, ovarian\_cancer, colorectal\_cancer, etc.)
- A minimum relative count
- A maximum age of onset (if applicable)
- A required degree of relation (first, second)
- A minimum number of generations represented (Lynch syndrome only)

If a rule's conditions are met, a high- or medium-priority alert is triggered with the specific reason and a referral recommendation.

**Benchmark — NCCN v2.2024 criteria (encoded directly):**

| Rule | Criteria | Flag |
|---|---|---|
| BRCA1/2 | 2+ first/second-degree relatives with breast cancer before age 50 | High |
| BRCA1/2 | 3+ relatives with breast cancer on same lineage | High |
| BRCA1/2 | 1 first-degree relative with breast cancer before age 40 | High |
| BRCA1/2 | Any ovarian cancer in first/second-degree relative | High |
| BRCA2 | Any male breast cancer in family | High |
| Lynch Syndrome | 3+ relatives with colorectal cancer across 2+ generations | High |
| Colorectal | 1 first-degree relative with colorectal cancer before age 50 | Medium |

**Benchmark — Ethnicity-based BRCA modifiers:**

| Ancestry | Modifier | Source |
|---|---|---|
| Ashkenazi Jewish | 10× BRCA carrier frequency | Struewing et al., NEJM 1997; King et al., Science 2003 |
| Icelandic | 4× BRCA2 carrier frequency | Published literature on BRCA2 999del5 |

---

### Onset Trend Analysis

**Formula — OLS Regression:**

```
slope, intercept = OLS_regression(generation_index, age_of_onset)
```

Applied across all affected relatives who have a recorded age of onset. Requires data points from at least 2 different generations. Slope classification:

| Slope | Classification |
|---|---|
| < −5 | strongly_accelerating |
| −5 to −2 | accelerating |
| −2 to +2 | stable |
| > +2 | decelerating |

A negative slope means the condition is appearing at a younger age each generation — a significant hereditary warning sign.

---

### Lifestyle Attribution

**Formula:**

```
combined_lifestyle_RR = product(RR_weight[flag] for each active flag in affected relatives)
excess_RR = family_RR - 1.0
lifestyle_excess = combined_lifestyle_RR - 1.0
lifestyle_attribution_fraction = clamp(lifestyle_excess / excess_RR, 0, 1)

genetic_predisposition_score = (1 - lifestyle_attribution_fraction) × (excess_RR / max_excess_RR) × 100
environmental_risk_score     = lifestyle_attribution_fraction × (excess_RR / max_excess_RR) × 100
```

Both scores are on a 0–100 scale. A high Environmental score means shared lifestyle (smoking, obesity, etc.) explains most of the elevated family risk. A high Genetic score means the pattern is predominantly inherited.

---

## Dashboard Tabs Explained

### Risk Gauges

Shows two types of cards depending on the condition:

**For diabetes and heart disease** — two semicircular gauges per condition:
- **Genetic score (0–100):** How much of the elevated risk is explained by hereditary factors.
- **Environmental score (0–100):** How much of the risk is explained by shared lifestyle factors.
- **RR (Relative Risk Ratio):** Your estimated risk compared to the general population. RR 2.0 = twice the baseline risk.

**For cancer conditions** — a rule-based flag card showing which NCCN or ethnicity criteria were triggered and the specific reasons.

### Onset Trends

A line chart plotting the age of diagnosis for each condition across generations. A downward slope means the condition is appearing at a younger age each generation — a significant warning sign. Requires data from at least two different generations to draw a trend line.

### Family Tree

An interactive genogram (clinical pedigree diagram) showing all entered family members colour-coded by risk level.

| Colour | Meaning |
|---|---|
| Red | High-risk condition affecting this relative |
| Orange | Medium-risk condition |
| Teal | Affected by a condition, no elevated risk flag |
| Dark blue | You (the proband) |

Square = male, Circle = female, Diamond = other. A † marks deceased relatives.

### Alerts

Prioritized clinical alerts:

| Priority | Triggers |
|---|---|
| **HIGH** | NCCN cancer red flag, ethnicity BRCA flag, RR ≥ 3.0, strongly accelerating onset trend, DPF ≥ 1.0, early-onset CVD |
| **MEDIUM** | RR ≥ 2.0, accelerating onset trend, DPF ≥ 0.7 |
| **LOW** | RR ≥ 1.5 |

Each alert includes a recommended clinical action.

### Raw JSON

The full engine output as JSON. Contains all scores, DPF values, onset trend slopes, lifestyle attribution fractions, and alert details.

---

## How to Use the Dashboard

### Step 1 — Enter your information (Proband)

In the left sidebar, fill in:
- **Your age** — used to calibrate risk thresholds and onset trend projections
- **Biological sex** — affects which cancer and CVD rules apply
- **Ancestry / ethnicity** — optional; activates ethnicity-specific risk modifiers (e.g. BRCA founder mutations in Ashkenazi Jewish populations)

### Step 2 — Select conditions to analyse

Choose one or more conditions from the multiselect dropdown.

**Supported conditions:**
- `diabetes`
- `heart_disease`
- `breast_cancer`
- `ovarian_cancer`
- `male_breast_cancer`
- `colorectal_cancer`
- `hypertension`

### Step 3 — Add family members

Click **+ Add family member** for each relative you have health information about.

| Field | What to enter |
|---|---|
| **Name** | Optional — for reference only |
| **Relationship** | e.g. mother, paternal\_grandfather, maternal\_great\_grandmother |
| **Sex** | The relative's biological sex |
| **Deceased** | Check if the relative has passed away |
| **Add condition** | Select a condition from the dropdown |
| **Age onset** | The age they were diagnosed (enter 0 if unknown) |
| **+ Add** | Click to save the condition to the member |
| **Lifestyle flags** | Checkboxes for shared risk factors |

Supported relationships include up to four generations:
- **Great-grandparents** (third generation): `paternal_great_grandfather`, `paternal_great_grandmother`, `maternal_great_grandfather`, `maternal_great_grandmother`
- **Grandparents** (second generation): `paternal_grandfather`, `paternal_grandmother`, etc.
- **Parents / aunts / uncles** (first generation): `father`, `mother`, `paternal_uncle`, etc.
- **Proband's generation**: `brother`, `sister`, `sibling`, `first_cousin`
- **Children**: `son`, `daughter`

### Step 4 — Analyse

Click **Analyse Family History**. Results appear instantly across five tabs.

---

## Example Scenarios

### Scenario 1 — BRCA Cancer Risk
**Setup:** Age 32, female, Ashkenazi Jewish ancestry. Add mother (breast cancer, age 44), maternal aunt (breast cancer, age 48), maternal grandmother (ovarian cancer, age 60).  
**Expected:** Multiple high-priority alerts — ethnicity BRCA flag, 2 breast cancer relatives under 50, ovarian cancer flag.

### Scenario 2 — Three-Generation CVD Pattern
**Setup:** Age 38, male. Add father (heart disease, age 48), paternal grandfather (heart disease, age 55), paternal great-grandfather (heart disease, age 60).  
**Expected:** Heart disease RR ~3.0, onset trend chart shows downward slope across three generations, high-priority CVD alert.

### Scenario 3 — Diabetes (Lifestyle vs Genetic)
**Setup:** Age 45, female. Add mother (diabetes, age 52, HighBP + HighChol flags), maternal grandmother (diabetes, age 60, HighBP), sister (diabetes, age 40, HighBP + Smoker).  
**Expected:** Elevated diabetes RR, Environmental score higher than Genetic score — shared lifestyle explains most of the risk.

---

## Key Terms

| Term | Plain English |
|---|---|
| **Proband** | You — the person being assessed |
| **Relative Risk Ratio (RR)** | Your risk compared to the general population. RR 2.0 = twice the average risk |
| **DPF Proxy** | Diabetes Pedigree Function — a score derived from how many first, second, and third-degree relatives have diabetes. Higher = more hereditary diabetes risk |
| **Genetic Predisposition Score** | 0–100 score of how much your elevated risk comes from inherited factors |
| **Environmental Risk Score** | 0–100 score of how much your elevated risk comes from shared lifestyle (diet, smoking, etc.) |
| **Lifestyle Attribution Fraction** | The proportion of family risk explained by shared lifestyle flags. 0 = fully genetic; 1 = fully lifestyle |
| **NCCN Red Flag** | A clinical criterion from the National Comprehensive Cancer Network guidelines v2.2024 |
| **BRCA1/2** | Genes associated with hereditary breast and ovarian cancer |
| **Lynch Syndrome** | A hereditary condition causing colorectal cancer |
| **First-degree relative** | Parent, sibling, or child — shares ~50% of your DNA |
| **Second-degree relative** | Grandparent, aunt, uncle — shares ~25% of your DNA |
| **Third-degree relative** | Great-grandparent — shares ~12.5% of your DNA |
| **Genogram** | A clinical pedigree diagram showing family structure with health information overlaid |
| **Onset Trend** | Whether a condition is appearing at a younger age in each successive generation |
| **OLS Regression** | Ordinary Least Squares — the statistical method used to draw the trend line across generations |
| **Early-onset CVD** | Heart disease diagnosed before age 55 (male) or 65 (female) — a significant hereditary risk marker |

---

## Technical Implementation

- **Engine:** Python — validates input, runs risk scoring, produces JSON output
- **Dashboard:** Streamlit + Plotly — interactive web UI, no server required
- **Datasets (offline reference):** BRFSS 2015 diabetes survey (253,680 rows), EarlyMed heart disease dataset (70,000 rows), Pima Indians diabetes dataset. Constants are pre-derived — CSVs are not loaded at runtime
- **Cancer rules:** NCCN Clinical Practice Guidelines in Oncology v2.2024
- **Ethnicity modifiers:** Published BRCA founder mutation prevalence literature

### Architecture

```
JSON input → validate_and_parse() → FamilyInput
                                        ↓
                              risk_scorer.score()  ← orchestrator
                             /        |          \
              hereditary_detector  onset_trend  lifestyle_filter
                     ↓                ↓               ↓
                  detection       onset trend    attribution scores
                     \               |              /
                      └────────── alert_builder ──┘
                                     ↓
                              JSON output dict
```

### Testing

```bash
# Install test dependencies
pipenv install --dev

# Start the app in one terminal
pipenv run streamlit run app.py

# Run Playwright UI tests in another terminal
pipenv run pytest tests/ -v

# Run with visible browser
pipenv run pytest tests/ -v --headed --slowmo 500
```
