"""
generate_data.py
-----------------
Creates a synthetic employee dataset for the DSPristine Employee Retention
Predictor. No real employee data is used anywhere in this project - this
script fabricates realistic-looking HR records with an underlying (but
noisy) relationship between employee attributes and attrition, so the
downstream model has real signal to learn from.

Run directly to (re)generate backend/data/employees.csv:
    python generate_data.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

RANDOM_SEED = 42
N_EMPLOYEES = 1500

DEPARTMENTS = ["Engineering", "Sales", "HR", "Finance", "Operations", "Customer Support"]
JOB_ROLES = {
    "Engineering": ["Software Engineer", "QA Engineer", "DevOps Engineer", "Tech Lead"],
    "Sales": ["Sales Executive", "Account Manager", "Sales Manager"],
    "HR": ["HR Executive", "Recruiter", "HR Manager"],
    "Finance": ["Financial Analyst", "Accountant", "Finance Manager"],
    "Operations": ["Operations Analyst", "Operations Manager"],
    "Customer Support": ["Support Executive", "Support Team Lead"],
}
BUSINESS_TRAVEL = ["Non-Travel", "Travel_Rarely", "Travel_Frequently"]
MARITAL_STATUS = ["Single", "Married", "Divorced"]
EDUCATION_FIELDS = ["Computer Science", "Business", "Commerce", "Arts", "Engineering", "Other"]


def generate_dataset(n=N_EMPLOYEES, seed=RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    age = rng.integers(21, 60, n)
    marital_status = rng.choice(MARITAL_STATUS, n, p=[0.42, 0.48, 0.10])
    distance_from_home = rng.integers(1, 40, n)
    department = rng.choice(DEPARTMENTS, n, p=[0.30, 0.22, 0.10, 0.12, 0.14, 0.12])
    job_role = np.array([rng.choice(JOB_ROLES[d]) for d in department])
    business_travel = rng.choice(BUSINESS_TRAVEL, n, p=[0.30, 0.55, 0.15])
    education_field = rng.choice(EDUCATION_FIELDS, n)

    job_satisfaction = rng.integers(1, 5, n)          # 1 (Low) - 4 (Very High)
    environment_satisfaction = rng.integers(1, 5, n)
    work_life_balance = rng.integers(1, 5, n)

    years_at_company = rng.integers(0, 25, n)
    years_since_last_promotion = np.minimum(
        rng.integers(0, 15, n), years_at_company
    )
    training_times_last_year = rng.integers(0, 6, n)
    overtime = rng.choice(["Yes", "No"], n, p=[0.30, 0.70])

    # Monthly income loosely tied to age / seniority / department, plus noise
    base_income = 25000 + years_at_company * 1800 + (age - 21) * 400
    dept_multiplier = pd.Series(department).map({
        "Engineering": 1.25, "Sales": 1.05, "HR": 0.95,
        "Finance": 1.10, "Operations": 1.0, "Customer Support": 0.9,
    }).to_numpy()
    monthly_income = (base_income * dept_multiplier + rng.normal(0, 4000, n)).clip(18000, 220000).round(-2)

    percent_salary_hike = rng.integers(10, 25, n)
    num_companies_worked = rng.integers(0, 8, n)

    # ---- Underlying attrition risk model (logits) ----
    # Higher risk with: low satisfaction, overtime, long commute, frequent
    # travel, long time since promotion, low pay hike, low income relative
    # to tenure, young + single, few years at company (early tenure churn).
    logit = (
        -2.6
        + (-0.55) * (job_satisfaction - 2.5)
        + (-0.35) * (environment_satisfaction - 2.5)
        + (-0.45) * (work_life_balance - 2.5)
        + 0.55 * (overtime == "Yes")
        + 0.02 * distance_from_home
        + 0.5 * (business_travel == "Travel_Frequently")
        + 0.12 * years_since_last_promotion
        - 0.05 * years_at_company
        - 0.10 * percent_salary_hike / 5
        - 0.000012 * (monthly_income - 60000)
        + 0.35 * (marital_status == "Single")
        + 0.25 * (num_companies_worked > 4)
        - 0.02 * (age - 30)
    )
    noise = rng.normal(0, 0.65, n)
    prob_attrition = 1 / (1 + np.exp(-(logit + noise)))
    attrition = (rng.random(n) < prob_attrition)
    attrition_label = np.where(attrition, "Yes", "No")

    employee_id = [f"EMP{100000 + i}" for i in range(n)]

    df = pd.DataFrame({
        "EmployeeID": employee_id,
        "Age": age,
        "MaritalStatus": marital_status,
        "DistanceFromHome": distance_from_home,
        "Department": department,
        "JobRole": job_role,
        "EducationField": education_field,
        "BusinessTravel": business_travel,
        "JobSatisfaction": job_satisfaction,
        "EnvironmentSatisfaction": environment_satisfaction,
        "WorkLifeBalance": work_life_balance,
        "YearsAtCompany": years_at_company,
        "YearsSinceLastPromotion": years_since_last_promotion,
        "TrainingTimesLastYear": training_times_last_year,
        "OverTime": overtime,
        "MonthlyIncome": monthly_income.astype(int),
        "PercentSalaryHike": percent_salary_hike,
        "NumCompaniesWorked": num_companies_worked,
        "Attrition": attrition_label,
    })
    return df


if __name__ == "__main__":
    out_dir = Path(__file__).parent / "data"
    out_dir.mkdir(exist_ok=True)
    df = generate_dataset()
    out_path = out_dir / "employees.csv"
    df.to_csv(out_path, index=False)
    print(f"Generated {len(df)} synthetic employee records -> {out_path}")
    print(df["Attrition"].value_counts(normalize=True).rename("share"))
