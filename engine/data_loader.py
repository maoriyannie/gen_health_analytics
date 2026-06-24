# engine/data_loader.py
# Lazy-cached dataset loaders. Used for calibration and reference, not runtime scoring.
# All analytics constants in benchmarks.py were derived from these datasets.

from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "datasets"

_CACHE: dict = {}


def _load(name: str, path: Path, **read_kwargs) -> pd.DataFrame:
    if name not in _CACHE:
        _CACHE[name] = pd.read_csv(path, **read_kwargs)
    return _CACHE[name]


def load_diabetes() -> pd.DataFrame:
    """
    Pima Indians Diabetes Dataset (768 rows).
    Key columns: DiabetesPedigreeFunction, Glucose, BMI, Age, Outcome.
    """
    df = _load("diabetes", DATA_DIR / "diabetes.csv")
    df = df.dropna(subset=["Outcome", "DiabetesPedigreeFunction"])
    df["Outcome"] = df["Outcome"].astype(int)
    return df


def load_heart_earlymed() -> pd.DataFrame:
    """
    Heart Disease Risk Dataset — EarlyMed (70,000 rows).
    Key columns: Family_History, Heart_Risk, Smoking, Obesity, Age, etc.
    All columns are binary (0/1) except Age (float).
    """
    df = _load("heart_earlymed", DATA_DIR / "heart_disease_risk_dataset_earlymed.csv")
    df = df.dropna(subset=["Heart_Risk"])
    binary_cols = [c for c in df.columns if c != "Age"]
    for col in binary_cols:
        df[col] = df[col].astype(int)
    df["Age"] = df["Age"].astype(float)
    return df


def load_brfss_full() -> pd.DataFrame:
    """
    BRFSS 2015 Diabetes Health Indicators — full dataset (253,680 rows).
    Key columns: Diabetes_012, HighBP, HighChol, BMI, Smoker, PhysActivity, Age, etc.
    """
    df = _load("brfss_full", DATA_DIR / "diabetes_012_health_indicators_BRFSS2015.csv")
    return df


def load_brfss_balanced() -> pd.DataFrame:
    """
    BRFSS 2015 — 50/50 balanced split (70,692 rows).
    Use this for model training to avoid class imbalance.
    Key column: Diabetes_binary.
    """
    df = _load(
        "brfss_balanced",
        DATA_DIR / "diabetes_binary_5050split_health_indicators_BRFSS2015.csv",
    )
    return df


def load_uci_heart() -> pd.DataFrame:
    """
    UCI Heart Disease Dataset — Cleveland + other centers (920 rows).
    Key columns: age, sex, chol, trestbps, num (diagnosis 0–4).
    Used for clinical benchmark reference (cholesterol/BP distributions).
    """
    df = _load("uci_heart", DATA_DIR / "heart_disease_uci.csv")
    for col in ["chol", "trestbps", "age"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["num"] = pd.to_numeric(df["num"], errors="coerce").fillna(0).astype(int)
    return df


def clear_cache() -> None:
    """Clear the in-memory dataset cache (useful in tests)."""
    _CACHE.clear()
