<div align="center">

# ⚡ PulseIQ — HR Intelligence Platform

### Enterprise-Grade AI Employee Performance Prediction System

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![Plotly](https://img.shields.io/badge/Plotly-5.x-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com)
[![ReportLab](https://img.shields.io/badge/ReportLab-PDF-E74C3C?style=for-the-badge)](https://www.reportlab.com)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)

<br/>

> **PulseIQ** is a full-stack, AI-powered HR analytics platform that predicts employee performance, generates professional PDF reports, surfaces actionable recommendations, and delivers enterprise-grade workforce intelligence — all in a single dark-theme dashboard.

<br/>


</div>

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Running the Application](#-running-the-application)
- [How It Works](#-how-it-works)
- [Dashboard Modules](#-dashboard-modules)
- [API Reference](#-api-reference)
- [PDF Report Engine](#-pdf-report-engine)
- [Score Engine](#-score-engine)
- [AI Recommendation Engine](#-ai-recommendation-engine)
- [Export Options](#-export-options)
- [Configuration](#-configuration)
- [Common Errors & Fixes](#-common-errors--fixes)
- [Future Roadmap](#-future-roadmap)
- [Author](#-author)

---

## 🧠 Overview

PulseIQ is built for HR teams, data scientists, and academic project showcases. It connects a **Flask ML backend** to a **Streamlit frontend** and delivers:

- Instant performance predictions (High / Medium / Low) for individual employees
- Bulk workforce analysis for entire departments or companies
- A built-in **Score Engine** that derives 11 HR intelligence metrics from model outputs
- An **AI Recommendation Engine** producing professional, section-wise HR guidance
- Fully designed **PDF reports** (single employee + bulk enterprise) with charts, tables, gauges, and recommendations — ready to hand to management
- All exports: **CSV, Excel, JSON, HTML, PDF**

This project is suitable for:

| Use Case | Why |
|---|---|
| 🎓 Final Year / Capstone Project | Complete end-to-end ML + dashboard stack |
| 🏆 Hackathon Submission | Impressive UI, live predictions, exportable reports |
| 💼 Portfolio Showcase | Enterprise-quality code with production patterns |
| 🏢 Placement / Interview Demo | Real-world HR analytics use case with AI reasoning |

---

## ✨ Key Features

### 🔮 Individual Intelligence Profiler
- 30+ field employee assessment form across 4 sections: Personal, Job, Performance, Behavioural
- 🎲 Random Employee Generator for instant demo data
- Real-time Flask API prediction with confidence scores
- **8 derived HR scores**: Health, Risk, Growth, Promotion Readiness, Retention, Productivity, Engagement, Soft Skills
- 4 animated Plotly gauges, dual radar charts, score waterfall decomposition
- **What-If Scenario Simulator** — adjust satisfaction, attendance, manager rating and see score deltas live
- Prediction history saved per session

### 🏢 Bulk Enterprise Analytics
- Upload CSV or XLSX with any number of employee records
- **10 live KPI cards**: Total, High/Mid/Low performers, promotion-ready, attrition risk, salary, satisfaction, attendance, experience
- **15+ interactive Plotly charts**: donut, stacked bar, scatter, histogram, box plot, violin, treemap, bubble, parallel coordinates, correlation heatmap, top/bottom 10 bars, trend area chart, age/gender distribution
- **10–12 AI-generated workforce insights** (auto-derived from data)
- Department-wise HR recommendation cards
- Interactive sortable/filterable leaderboard table
- Graceful demo mode — works even when Flask API is offline (synthesises predictions)

### 📄 PDF Report Engine (hr_pdf_engine.py)
- **Single Employee PDF** (5 pages): cover, prediction scorecard, gauges, employee profile tables, radar charts, score bars, waterfall, all recommendation sections, KPI benchmark table
- **Bulk Enterprise PDF** (8 sections): cover, KPI dashboard, performance analytics, attrition/promotion gauges, top/bottom performers, correlation matrix, AI insights, department recommendations, 50-employee leaderboard table
- Print-safe light theme — white backgrounds, black text, fully readable on paper
- Branded header + footer on every page with page numbers and confidentiality notice

### 📤 Exports
| Format | Single Employee | Bulk Workforce |
|--------|----------------|----------------|
| CSV    | ✅ Intelligence Report | ✅ Full Dataset |
| JSON   | ✅ Structured Report | — |
| Excel  | — | ✅ Executive Summary (multi-sheet) |
| PDF    | ✅ 5-page HR Report | ✅ 8-section Enterprise Report |
| HTML   | — | ✅ Standalone Dashboard |

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Streamlit 1.x · Custom CSS (Glassmorphism, Dark Theme) |
| **Charting** | Plotly 5.x (interactive) · Matplotlib (PDF charts) |
| **Backend API** | Flask 3.x · REST JSON API |
| **ML Model** | Scikit-learn (via Flask) |
| **PDF Engine** | ReportLab 4.x · Matplotlib (chart rendering) |
| **Data** | Pandas 2.x · NumPy |
| **Exports** | openpyxl (Excel) · json · io |
| **Fonts** | Syne · DM Sans · JetBrains Mono (via Google Fonts) |

---

## 📁 Project Structure

```
Employee-Performance-Prediction-System/
│
├── app/                                  ← Streamlit frontend + PDF engine
│   ├── streamlit_dashboard.py            ← Main dashboard (1 900+ lines)
│   └── hr_pdf_engine.py                  ← PDF report generator (1 300+ lines)
│
├── model/                                ← Flask ML backend
│   ├── app.py                            ← Flask server with API endpoints
│   ├── model.pkl                         ← Trained ML model (pickle)
│   └── label_encoder.pkl                 ← Label encoder (if used)
│
├── data/
│   ├── raw/                              ← Original HR dataset
│   └── cleaned/
│       └── ml_features.csv               ← Preprocessed features (optional benchmark)
│
├── notebooks/
│   └── model_training.ipynb              ← EDA + model training notebook
│
├── requirements.txt                      ← Python dependencies
└── README.md                             ← This file
```

> **Note:** `streamlit_dashboard.py` and `hr_pdf_engine.py` **must be in the same folder** — the dashboard auto-injects its own directory into `sys.path` at startup to ensure the PDF engine is always found.

---

## ⚙️ Installation

### Prerequisites

- Python 3.10 or higher
- pip
- Git

### Step 1 — Clone the repository

```bash
git clone https://github.com/yourusername/Employee-Performance-Prediction-System.git
cd Employee-Performance-Prediction-System
```

### Step 2 — Create a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt** (minimum):

```txt
streamlit>=1.32.0
flask>=3.0.0
plotly>=5.20.0
pandas>=2.0.0
numpy>=1.26.0
scikit-learn>=1.4.0
matplotlib>=3.8.0
reportlab>=4.0.0
openpyxl>=3.1.0
requests>=2.31.0
```

---

## 🚀 Running the Application

PulseIQ has two independent processes — start **both** in separate terminals.

### Terminal 1 — Start the Flask ML API

```bash
cd model
python app.py
```

You should see:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: off
```

### Terminal 2 — Start the Streamlit Dashboard

```bash
cd app
streamlit run streamlit_dashboard.py
```

The dashboard opens automatically at **http://localhost:8501**

> **Tip:** The dashboard works in **demo mode** even if Flask is offline — it will show a warning banner and synthesise predictions so you can still demo the UI and charts.

---

## 🔄 How It Works

```
┌─────────────────────────────────────────────────────────┐
│                    USER BROWSER                         │
│              http://localhost:8501                      │
└──────────────────────┬──────────────────────────────────┘
                       │  Streamlit UI
                       ▼
┌─────────────────────────────────────────────────────────┐
│              streamlit_dashboard.py                     │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Tab 1      │  │   Tab 2      │  │    Tab 3      │  │
│  │  Individual │  │   Bulk       │  │  Prediction   │  │
│  │  Profiler   │  │  Analytics   │  │   History     │  │
│  └──────┬──────┘  └──────┬───────┘  └───────────────┘  │
│         │                │                              │
│         ▼                ▼                              │
│   compute_scores()  bulk_ensure_columns()               │
│   generate_recs()   bulk_generate_insights()            │
│   viz_*()           bulk_recommendations_by_dept()      │
│         │                │                              │
│         └────────────────┘                              │
│                  │  PDF                                 │
│                  ▼                                      │
│           hr_pdf_engine.py                              │
│    generate_single_pdf() / generate_bulk_pdf()          │
└──────────────────┬──────────────────────────────────────┘
                   │  HTTP POST (requests)
                   ▼
┌─────────────────────────────────────────────────────────┐
│                  Flask API  :5000                       │
│                                                         │
│   POST /predict-performance  →  single prediction       │
│   POST /bulk-predict         →  bulk predictions        │
│                                                         │
│   model.pkl  ──►  scikit-learn  ──►  JSON response      │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Dashboard Modules

### Tab 1 — Individual Intelligence Profiler

#### Assessment Form — 4 Sections

| Section | Fields |
|---|---|
| 👤 Personal Information | Name, Employee ID, Age, Gender, Department, Job Role, Education, Marital Status |
| 💼 Job Information | Monthly Income, Years at Company, Years in Role, Years Since Promotion, Total Experience, Business Travel, Overtime, Distance from Home |
| 📊 Performance Metrics | Job Satisfaction, Environment Satisfaction, Relationship Satisfaction, Work-Life Balance, Attendance Rate, Manager Rating, Training Hours, No. of Projects, Self Performance Rating |
| 🧠 Behavioural Assessment | Job Involvement, Work Environment Score, Innovation Score, Leadership Score, Communication Score, Team Collaboration Score |

#### Result Dashboard

- **Prediction Card** — High / Medium / Low with AI reasoning summary
- **Confidence Breakdown** — bar chart of probability per class
- **8-score KPI Scorecard** — colour-coded metric cards
- **4 Gauges** — Health, Attrition Risk, Promotion Readiness, Retention
- **Dual Radar Charts** — Performance Radar + Soft Skills Spider
- **Score Breakdown Bar** — all 8 scores horizontally
- **HR Score Waterfall** — contribution of each factor to the final score
- **Workforce Benchmark Scatter** — your employee vs. company population
- **What-If Simulator** — adjust 3 inputs and see live score changes
- **AI Recommendation Engine** — 9 expandable professional recommendation sections

### Tab 2 — Bulk Enterprise Analytics

Upload a CSV/XLSX → click **Execute Bulk Intelligence Pipeline** → full dashboard renders instantly.

**Charts included:**

| Chart | Type |
|---|---|
| Performance Distribution | Donut |
| Department Performance | Stacked Bar |
| HR Matrix | Scatter (Attrition vs Promotion) |
| Salary Distribution | Histogram (by tier) |
| Satisfaction Distribution | Box Plot |
| Attendance Distribution | Violin Plot |
| Age Group vs Performance | Grouped Bar |
| Gender Distribution | Pie |
| Department Treemap | Treemap |
| Experience vs Income | Bubble |
| Correlation Matrix | Heatmap |
| Attrition Risk Bands | Donut |
| Top 10 Performers | Horizontal Bar |
| Bottom 10 — Needs Attention | Horizontal Bar |
| Score Trends by Tenure | Area + Line |
| Multi-Dimensional View | Parallel Coordinates |

### Tab 3 — Prediction History

- Session-level log of every individual prediction run
- Columns: Timestamp, Name, ID, Department, Prediction, Confidence, HR Score
- Clear history button

---

## 🌐 API Reference

Both endpoints are defined in your Flask `app.py`.

### `POST /predict-performance`

Predict performance for a single employee.

**Request Body:**
```json
{
  "Age": 32,
  "MonthlyIncome": 75000,
  "YearsAtCompany": 5,
  "satisfaction_score": 3.2,
  "AttendanceRate": 95.0,
  "OverTime": "No",
  "BusinessTravel": "Travel_Rarely",
  "EnvironmentSatisfaction": 3,
  "RelationshipSatisfaction": 3,
  "WorkLifeBalance": 3,
  "JobInvolvement": 3,
  "ManagerRating": 3.8,
  "PerformanceRating": 3,
  "YearsInCurrentRole": 3,
  "YearsSinceLastPromotion": 1,
  "TotalWorkingYears": 8,
  "TrainingTimesLastYear": 25,
  "NumCompaniesWorked": 3,
  "DistanceFromHome": 10
}
```

**Response:**
```json
{
  "prediction": "High",
  "probabilities": {
    "High": 0.82,
    "Medium": 0.13,
    "Low": 0.05
  }
}
```

---

### `POST /bulk-predict`

Predict performance for multiple employees at once.

**Request Body:**
```json
[
  { "Age": 32, "MonthlyIncome": 75000, "satisfaction_score": 3.2, ... },
  { "Age": 45, "MonthlyIncome": 55000, "satisfaction_score": 2.1, ... }
]
```

**Response:**
```json
{
  "results": [
    { "Prediction": "High", "probabilities": { ... }, ... },
    { "Prediction": "Low",  "probabilities": { ... }, ... }
  ]
}
```

> **Graceful fallback:** If the API is unreachable, the dashboard synthesises predictions from the uploaded data and shows a warning. All charts, insights, recommendations, and PDF exports still work in this demo mode.

---

## 📄 PDF Report Engine

The PDF engine (`hr_pdf_engine.py`) is a standalone module — no browser or Chrome required. All charts are rendered via **Matplotlib** and embedded directly into the PDF using **ReportLab**.

### Single Employee PDF — 5 Pages

| Page | Content |
|---|---|
| Cover | PulseIQ branding, employee name, prediction summary, confidence, HR score |
| 01 · AI Prediction Result | Prediction banner, 8-score KPI cards, 4 gauges, probability bar chart |
| 02 · Employee Profile | Personal, Job, Performance and Behavioural data tables |
| 03 · Performance Visualisations | Dual radar charts, score breakdown bar, HR score waterfall |
| 04 · AI Recommendation Engine | 9 colour-coded recommendation sections |
| 05 · KPI Summary Table | All 8 scores vs. company benchmark with Above/Below status |

### Bulk Enterprise PDF — 8 Sections

| Section | Content |
|---|---|
| Cover | Workforce summary, high-level KPIs |
| 01 · Enterprise KPI Dashboard | 10 KPI metric cards |
| 02 · Performance Analytics | Donut, dept bar, salary histogram, experience scatter, age/gender charts |
| 03 · Attrition & Promotion | 3 gauges, attrition vs promotion scatter |
| 04 · Top & Bottom Performers | Two horizontal bar leaderboards |
| 05 · Correlation Matrix | Full statistical heatmap |
| 06 · AI Insights | 10–12 auto-generated workforce observations |
| 07 · Department Recommendations | Per-department HR action items |
| 08 · Employee Leaderboard | Top-50 styled table with conditional row colouring |

### PDF Design Specs

- **Page size:** A4
- **Backgrounds:** White (print-safe)
- **Text:** Black (#111111) for readability
- **Accents:** Cyan (#00e5ff) borders and section headers
- **Header:** Navy bar with cyan accent line on every page
- **Footer:** Confidentiality notice + auto page numbers
- **Charts:** Matplotlib dark-theme (CARD background) embedded as PNG at 140 DPI

---

## 🧮 Score Engine

`compute_scores()` derives 11 HR intelligence metrics entirely from the model output and form inputs — no extra API calls needed.

| Score | Formula Inputs | Range |
|---|---|---|
| **Confidence** | `max(probabilities)` | 0–100 |
| **Performance** | Mapped from prediction label | 30 / 60 / 85 |
| **Health Score** | Satisfaction + WLB + Attendance + Environment Satisfaction | 0–100 |
| **Risk Score** | Attendance < 85 + Low satisfaction + Overtime + Low income + No promotion + Low manager rating | 0–100 |
| **Growth Score** | Total experience + Training hours + Manager rating + No. of projects | 0–100 |
| **Promotion Readiness** | Manager rating + Tenure + Performance + Training + Projects | 0–100 |
| **Retention Probability** | 100 − Risk + Satisfaction + Tenure | 0–100 |
| **Productivity** | Attendance + Job Involvement + Performance + Projects | 0–100 |
| **Engagement** | Satisfaction + Relationship Satisfaction + WLB + Job Involvement + Environment | 0–100 |
| **Soft Skills** | (Innovation + Leadership + Communication + Team Collaboration) / 4 | 0–100 |
| **Overall HR Score** | Weighted composite of all above | 0–100 |

---

## 🤖 AI Recommendation Engine

`generate_recommendations()` produces structured, professional HR guidance across **9 categories** based on scores, thresholds, and contextual logic:

| Category | Example Output |
|---|---|
| ✅ Strengths | Flags exceptional attendance, high satisfaction, strong manager rating |
| ⚠️ Weaknesses | Identifies low attendance, satisfaction, stagnation, burnout signals |
| 🚀 Career Growth | Succession pipeline nomination, IDP creation, lateral transfer options |
| 📚 Training Roadmap | Training hour gaps, AI literacy, leadership foundations programme |
| 💰 Compensation Review | Market benchmark comparison, merit increase percentage recommendations |
| 👑 Leadership Development | Manager candidate flagging, client-facing role readiness |
| 💚 Employee Wellness | EAP access, wellbeing check-ins, social event participation |
| 🔒 Attrition Prevention | CRITICAL escalation for risk ≥ 70, retention package suggestions |
| 📋 Action Items | 1-on-1 scheduling, IDP updates, PIP initiation, recognition awards |

Each recommendation is **contextual** — it reads the employee's actual data, not generic advice. It also generates an **Executive Summary** paragraph suitable for a manager's briefing.

---

## 📤 Export Options

### Single Employee
```
📥 CSV Intelligence Report     → employee_name_HR_Report.csv
📄 PDF Intelligence Report     → employee_name_HR_Report.pdf   (5 pages)
📊 JSON Intelligence Report    → employee_name_HR_Report.json
```

### Bulk Workforce
```
📥 CSV Report                  → enterprise_bulk_report.csv
📄 PDF Enterprise Report       → enterprise_hr_report.pdf      (8 sections)
📊 Excel Executive Report      → enterprise_executive_report.xlsx (2 sheets)
🌐 HTML Dashboard              → enterprise_hr_dashboard.html
```

---

## ⚙️ Configuration

All key settings are at the top of `streamlit_dashboard.py`:

```python
# ── API endpoints — change if Flask runs on a different port ──
API_BASE        = "http://127.0.0.1:5000"
SINGLE_ENDPOINT = f"{API_BASE}/predict-performance"
BULK_ENDPOINT   = f"{API_BASE}/bulk-predict"

# ── Dropdown options — extend as needed ──
DEPARTMENTS     = ["Sales", "Research & Development", "Human Resources", ...]
JOB_ROLES       = ["Sales Executive", "Research Scientist", ...]

# ── Theme colors ──
C_ACCENT1 = "#00e5ff"   # electric cyan — primary accent
C_ACCENT2 = "#a855f7"   # violet — secondary accent
C_HIGH    = "#22c55e"   # green — high performance
C_MEDIUM  = "#eab308"   # yellow — medium performance
C_LOW     = "#ef4444"   # red — low performance / high risk
```

To **rename the platform** from PulseIQ to your own name, find and replace `PulseIQ` in both files:
- `streamlit_dashboard.py` — appears in page title, hero banner, footer (~5 places)
- `hr_pdf_engine.py` — appears in PDF cover, header, footer (~6 places)

---


## 🐛 Common Errors & Fixes

| Error | Cause | Fix |
|---|---|---|
| `PDF engine not found` | `hr_pdf_engine.py` not in `app/` folder | Place both `.py` files in the same directory |
| `Cannot reach Flask API` | Flask server not running | Run `python app.py` in the `model/` folder first |
| `TypeError: Object of type int32 is not JSON serializable` | NumPy types in JSON output | Already fixed — `_NpEncoder` handles this globally |
| `got multiple values for keyword argument 'margin'` | `PLOTLY_THEME` has `margin` key | Already fixed — use `PLOTLY_THEME_NM` for calls with explicit margin |
| `ValueError: Invalid value '#ef444418' for color` | 8-digit hex not supported by Plotly | Already fixed — converted to `rgba()` format |
| `Attrition Risk Distribution chart empty` | Pandas 2.x `pd.cut().value_counts()` column naming | Already fixed — uses explicit boolean bucketing |
| `streamlit: command not found` | Virtual environment not activated | Run `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux) |
| Blank PDF tables (white on white) | Dark theme colors carried into PDF | Already fixed — PDF engine uses print-safe light palette |

---

## 🗺 Future Roadmap

- [ ] **Authentication** — Login page with role-based access (HR Manager vs. Viewer)
- [ ] **Database Integration** — PostgreSQL / SQLite persistence for prediction history
- [ ] **Live Retraining** — Upload new labelled data and retrain the model in-browser
- [ ] **Email Reports** — Send PDF reports directly to manager inboxes via SMTP
- [ ] **Multi-Language Support** — i18n for Arabic, French, Spanish HR teams
- [ ] **Mobile Responsive View** — Tailored layout for tablet/phone HR access
- [ ] **SHAP Explanations** — Feature-level model explainability in the dashboard
- [ ] **Power BI Connector** — Export data in Power BI-compatible format
- [ ] **Succession Planning Module** — Visual org-chart with promotion pipeline tracking
- [ ] **Automated Scheduling** — Periodic bulk prediction runs with scheduled email digests

---

## 👤 Author

**Aarthi S**
Final Year Student · Department of Information Technology / Data Science / AI


---

<div align="center">

**Built with ❤️ using Python · Flask · Streamlit · Plotly · ReportLab**

*PulseIQ — Because every employee deserves intelligent HR decisions.*


</div>
