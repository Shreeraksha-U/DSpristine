# DSPristine Retention Radar

An employee retention (attrition) predictor for DSPristine HRMS. Enter an
employee's profile and get a **Stay / Leave** prediction with a probability
score, plus an HR dashboard of attrition trends, model feature importance,
and a ranked at-risk employee list.

- **Model:** scikit-learn `RandomForestClassifier` (a `DecisionTreeClassifier`
  is also trained for comparison; whichever scores higher on ROC-AUC is
  served in production — currently the Random Forest).
- **Data:** a synthetic employee dataset generated locally (`backend/generate_data.py`).
  **No real employee data is included or required.** The synthetic data has
  a deliberately built-in (but noisy) relationship between attributes like
  overtime, satisfaction, commute distance, and pay — so the model has real
  signal to learn from, without touching any actual HR records.
- **Backend:** Flask REST API (`backend/app.py`).
- **Frontend:** plain HTML/CSS/JS (no build step), calling the Flask API.

## Project structure

```
retention-predictor/
├── backend/
│   ├── app.py              # Flask API + serves the frontend
│   ├── generate_data.py    # synthetic dataset generator
│   ├── train_model.py      # trains Decision Tree + Random Forest
│   ├── requirements.txt
│   ├── .env.example        # copy to .env (never commit .env)
│   ├── data/                # generated CSV lands here (git-ignored)
│   └── model/                # generated .joblib + metadata.json (git-ignored)
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   └── js/
│       ├── config.js       # API base URL
│       ├── api.js          # fetch helper
│       ├── charts.js       # Chart.js dashboard visuals
│       ├── predict.js      # prediction form + gauge
│       ├── atrisk.js       # at-risk employee table
│       ├── main.js         # tab routing + bootstrap
│       └── vendor/chart.umd.js   # Chart.js, vendored locally (no CDN dependency)
├── .gitignore
└── README.md
```

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # adjust values if needed, never commit .env

python app.py
```

Open **http://localhost:5000** — the Flask app serves both the API and the
frontend, so nothing else needs to run.

The very first request trains the model automatically if `backend/model/`
is empty (takes a few seconds). To retrain manually or regenerate the
dataset at any time:

```bash
python generate_data.py   # regenerate synthetic employees.csv
python train_model.py     # retrain Decision Tree + Random Forest
```

## Environment variables (`backend/.env`)

| Variable        | Purpose                                              | Default        |
|-----------------|-------------------------------------------------------|----------------|
| `PORT`          | Port Flask runs on                                    | `5000`         |
| `FLASK_DEBUG`   | `true`/`false` — keep `false` outside local dev        | `false`        |
| `MODEL_TYPE`    | Which trained pipeline to serve: `random_forest` or `decision_tree` | `random_forest` |
| `ALLOWED_ORIGIN`| CORS origin allowed to call `/api/*`                   | `*`            |

`.env` is git-ignored. Only `.env.example` (no real secrets) is committed.

## API endpoints

| Method | Path                     | Purpose                                   |
|--------|---------------------------|--------------------------------------------|
| GET    | `/api/health`             | Liveness check                            |
| GET    | `/api/meta`                | Form field options, model metrics         |
| POST   | `/api/predict`             | Predict Stay/Leave for one employee       |
| GET    | `/api/feature-importance`  | Top attrition drivers                     |
| GET    | `/api/eda`                  | Aggregated attrition stats for charts     |
| GET    | `/api/at-risk?limit=40`     | Ranked list of at-risk active employees   |


## Note on data

This project ships with **synthetic, fabricated data only**. No real
DSPristine or Dyashin Technosoft employee information is used, stored, or
required to run this project.

## Note on models
train_model.py trains both a Decision Tree and a Random Forest on the same data of over 1,500 records, evaluates each (accuracy, precision, recall, F1, ROC-AUC), and saves both as .joblib files plus a metadata.json recording both sets of metrics.
Whichever scored higher ROC-AUC is marked the "production" model. Currently that's the Random Forest (~0.71 ROC-AUC vs. the Decision Tree's ~0.60).
The Flask app (app.py) loads just one of them at startup, controlled by the MODEL_TYPE variable in .env file (random_forest or decision_tree). That single model is what actually answers every /api/predict call, powers the At-Risk list, and drives the feature-importance chart.

It's "train both, pick the better one, serve that one"
