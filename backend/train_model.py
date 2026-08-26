"""
train_model.py
---------------
Trains the Employee Retention classifier for DSPristine.

Two candidate models are trained - a DecisionTreeClassifier (fully
interpretable, easy to explain to HR stakeholders) and a
RandomForestClassifier (usually more accurate, still gives feature
importances). Whichever scores higher on held-out ROC-AUC is saved as the
"production" model, but both are kept on disk with their metrics so the
choice is transparent.

Run directly:
    python train_model.py
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                              recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from generate_data import generate_dataset

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "employees.csv"
MODEL_DIR = BASE_DIR / "model"

NUMERIC_FEATURES = [
    "Age", "DistanceFromHome", "JobSatisfaction", "EnvironmentSatisfaction",
    "WorkLifeBalance", "YearsAtCompany", "YearsSinceLastPromotion",
    "TrainingTimesLastYear", "MonthlyIncome", "PercentSalaryHike",
    "NumCompaniesWorked",
]
CATEGORICAL_FEATURES = [
    "MaritalStatus", "Department", "JobRole", "EducationField",
    "BusinessTravel", "OverTime",
]
TARGET = "Attrition"


def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        DATA_PATH.parent.mkdir(exist_ok=True)
        df = generate_dataset()
        df.to_csv(DATA_PATH, index=False)
    return pd.read_csv(DATA_PATH)


def build_pipeline(estimator) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )
    return Pipeline(steps=[("preprocessor", preprocessor), ("model", estimator)])


def get_feature_names(pipeline: Pipeline):
    preprocessor = pipeline.named_steps["preprocessor"]
    cat_encoder = preprocessor.named_transformers_["cat"]
    cat_names = list(cat_encoder.get_feature_names_out(CATEGORICAL_FEATURES))
    return NUMERIC_FEATURES + cat_names


def evaluate(pipeline: Pipeline, X_test, y_test) -> dict:
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]
    return {
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, pos_label=1), 4),
        "recall": round(recall_score(y_test, y_pred, pos_label=1), 4),
        "f1": round(f1_score(y_test, y_pred, pos_label=1), 4),
        "roc_auc": round(roc_auc_score(y_test, y_proba), 4),
    }


def main():
    MODEL_DIR.mkdir(exist_ok=True)
    df = load_data()

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = (df[TARGET] == "Yes").astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    candidates = {
        "decision_tree": DecisionTreeClassifier(
            max_depth=6, min_samples_leaf=15, class_weight="balanced", random_state=42
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300, max_depth=10, min_samples_leaf=5,
            class_weight="balanced", random_state=42, n_jobs=-1
        ),
    }

    results = {}
    fitted = {}
    for name, estimator in candidates.items():
        pipeline = build_pipeline(estimator)
        pipeline.fit(X_train, y_train)
        metrics = evaluate(pipeline, X_test, y_test)
        results[name] = metrics
        fitted[name] = pipeline
        print(f"[{name}] {metrics}")

    best_name = max(results, key=lambda n: results[n]["roc_auc"])
    best_pipeline = fitted[best_name]
    print(f"\nSelected production model: {best_name} (highest ROC-AUC)")

    # Feature importances from the *production* model
    importances = best_pipeline.named_steps["model"].feature_importances_
    feature_names = get_feature_names(best_pipeline)
    importance_pairs = sorted(
        zip(feature_names, importances), key=lambda p: p[1], reverse=True
    )
    top_importances = [
        {"feature": f, "importance": round(float(v), 5)}
        for f, v in importance_pairs[:12]
    ]

    # Save both pipelines (so the app/API can expose either if desired)
    for name, pipeline in fitted.items():
        joblib.dump(pipeline, MODEL_DIR / f"{name}.joblib")

    metadata = {
        "production_model": best_name,
        "metrics": results,
        "feature_importances": top_importances,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "categorical_options": {
            col: sorted(df[col].unique().tolist()) for col in CATEGORICAL_FEATURES
        },
        "n_train": len(X_train),
        "n_test": len(X_test),
        "attrition_rate": round(float(y.mean()), 4),
    }
    with open(MODEL_DIR / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nSaved model artifacts to {MODEL_DIR}/")


if __name__ == "__main__":
    main()
