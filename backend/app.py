"""
app.py
------
Flask API for the DSPristine Employee Retention Predictor.

Endpoints:
    GET  /api/health            - simple liveness check
    GET  /api/meta              - form options, feature list, model metrics
    POST /api/predict           - predict Stay/Leave for one employee
    GET  /api/feature-importance- top drivers of attrition
    GET  /api/eda               - aggregated stats for dashboard charts
    GET  /api/at-risk           - ranked list of current at-risk employees

Also serves the static frontend (../frontend) so the whole app can be run
with a single `python app.py`.

Configuration is read from environment variables (see .env.example).
Nothing sensitive is hardcoded here - copy .env.example to .env locally.
"""

import os
from pathlib import Path

import joblib
import pandas as pd
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from train_model import (CATEGORICAL_FEATURES, NUMERIC_FEATURES, main as
                          train_and_save_model)

load_dotenv()

BASE_DIR = Path(__file__).parent
MODEL_DIR = BASE_DIR / "model"
DATA_PATH = BASE_DIR / "data" / "employees.csv"
FRONTEND_DIR = BASE_DIR.parent / "frontend"

PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
MODEL_NAME = os.getenv("MODEL_TYPE", "random_forest")  # random_forest | decision_tree
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGIN}})


def ensure_model_ready():
    """Train on first run if artifacts are missing (keeps repo git-safe -
    no large binary model files need to be committed)."""
    required = [MODEL_DIR / "random_forest.joblib", MODEL_DIR / "decision_tree.joblib",
                MODEL_DIR / "metadata.json"]
    if not all(p.exists() for p in required):
        print("Model artifacts not found - training now (first run only)...")
        train_and_save_model()


ensure_model_ready()

import json  # noqa: E402  (after ensure_model_ready so metadata definitely exists)

with open(MODEL_DIR / "metadata.json") as f:
    METADATA = json.load(f)

PIPELINE = joblib.load(MODEL_DIR / f"{MODEL_NAME}.joblib")
EMPLOYEES_DF = pd.read_csv(DATA_PATH) if DATA_PATH.exists() else pd.DataFrame()


# ---------------------------------------------------------------- helpers --
def build_feature_frame(payload: dict) -> pd.DataFrame:
    row = {}
    for col in NUMERIC_FEATURES:
        row[col] = [float(payload.get(col, 0))]
    for col in CATEGORICAL_FEATURES:
        row[col] = [payload.get(col, "")]
    return pd.DataFrame(row)


# ------------------------------------------------------------------ routes --
@app.route("/api/health")
def health():
    return jsonify(status="ok", model=MODEL_NAME)


@app.route("/api/meta")
def meta():
    return jsonify({
        "numeric_features": METADATA["numeric_features"],
        "categorical_features": METADATA["categorical_features"],
        "categorical_options": METADATA["categorical_options"],
        "model_name": MODEL_NAME,
        "metrics": METADATA["metrics"].get(MODEL_NAME, {}),
        "attrition_rate": METADATA["attrition_rate"],
        "n_train": METADATA["n_train"],
        "n_test": METADATA["n_test"],
    })


@app.route("/api/predict", methods=["POST"])
def predict():
    payload = request.get_json(force=True) or {}

    missing = [c for c in NUMERIC_FEATURES + CATEGORICAL_FEATURES
               if c not in payload or payload[c] in (None, "")]
    if missing:
        return jsonify(error=f"Missing fields: {', '.join(missing)}"), 400

    try:
        X = build_feature_frame(payload)
        proba_leave = float(PIPELINE.predict_proba(X)[0][1])
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=f"Prediction failed: {exc}"), 400

    label = "Leave" if proba_leave >= 0.5 else "Stay"
    risk_band = (
        "High" if proba_leave >= 0.6 else
        "Medium" if proba_leave >= 0.35 else
        "Low"
    )

    return jsonify({
        "prediction": label,
        "leave_probability": round(proba_leave, 4),
        "stay_probability": round(1 - proba_leave, 4),
        "risk_band": risk_band,
        "model_used": MODEL_NAME,
    })


@app.route("/api/feature-importance")
def feature_importance():
    return jsonify(features=METADATA["feature_importances"])


@app.route("/api/eda")
def eda():
    if EMPLOYEES_DF.empty:
        return jsonify(error="No dataset available"), 404
    df = EMPLOYEES_DF

    def rate_by(col):
        g = df.groupby(col)["Attrition"].apply(lambda s: (s == "Yes").mean())
        return [{"label": str(k), "attrition_rate": round(float(v), 4)} for k, v in g.items()]

    overtime_rate = rate_by("OverTime")
    travel_rate = rate_by("BusinessTravel")
    dept_rate = rate_by("Department")
    satisfaction_rate = rate_by("JobSatisfaction")

    income_bins = pd.cut(
        df["MonthlyIncome"],
        bins=[0, 30000, 50000, 80000, 120000, 1_000_000],
        labels=["<30k", "30-50k", "50-80k", "80-120k", "120k+"],
    )
    income_rate = (
        df.assign(IncomeBand=income_bins)
        .groupby("IncomeBand", observed=True)["Attrition"]
        .apply(lambda s: (s == "Yes").mean())
    )
    income_rate = [{"label": str(k), "attrition_rate": round(float(v), 4)} for k, v in income_rate.items()]

    return jsonify({
        "total_employees": int(len(df)),
        "overall_attrition_rate": round(float((df["Attrition"] == "Yes").mean()), 4),
        "by_overtime": overtime_rate,
        "by_business_travel": travel_rate,
        "by_department": dept_rate,
        "by_job_satisfaction": satisfaction_rate,
        "by_income_band": income_rate,
    })


@app.route("/api/at-risk")
def at_risk():
    if EMPLOYEES_DF.empty:
        return jsonify(error="No dataset available"), 404

    limit = int(request.args.get("limit", 25))
    df = EMPLOYEES_DF.copy()
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    df["leave_probability"] = PIPELINE.predict_proba(X)[:, 1]

    currently_active = df[df["Attrition"] == "No"].copy()
    currently_active.sort_values("leave_probability", ascending=False, inplace=True)
    top = currently_active.head(limit)

    records = top[[
        "EmployeeID", "Department", "JobRole", "Age", "YearsAtCompany",
        "MonthlyIncome", "JobSatisfaction", "OverTime", "leave_probability",
    ]].copy()
    records["leave_probability"] = records["leave_probability"].round(4)
    records["risk_band"] = records["leave_probability"].apply(
        lambda p: "High" if p >= 0.6 else "Medium" if p >= 0.35 else "Low"
    )

    return jsonify(employees=records.to_dict(orient="records"))


# --------------------------------------------------------- static frontend --
@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(FRONTEND_DIR, path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
