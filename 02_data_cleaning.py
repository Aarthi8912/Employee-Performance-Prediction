"""
02_data_cleaning.py
HR Analytics Platform — Data Cleaning, Feature Engineering & EDA
INX Future Inc. Dataset
"""

import os, warnings, random, json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')
np.random.seed(42)
random.seed(42)

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, 'data', 'cleaned')
RAW_DIR    = BASE_DIR
REPORTS    = os.path.join(BASE_DIR, 'reports')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REPORTS,  exist_ok=True)

print("=" * 60)
print("  HR Analytics Platform — Data Cleaning Pipeline")
print("=" * 60)

# ─────────────────────────────────────────────────────────────
# 1. LOAD RAW DATA
# ─────────────────────────────────────────────────────────────
print("\n[1/8] Loading raw datasets...")
general   = pd.read_csv(os.path.join(RAW_DIR, 'general_data.csv'))
emp_surv  = pd.read_csv(os.path.join(RAW_DIR, 'employee_survey_data.csv'))
mgr_surv  = pd.read_csv(os.path.join(RAW_DIR, 'manager_survey_data.csv'))
in_time   = pd.read_csv(os.path.join(RAW_DIR, 'in_time.csv'), index_col=0)
out_time  = pd.read_csv(os.path.join(RAW_DIR, 'out_time.csv'), index_col=0)

print(f"  general_data      : {general.shape}")
print(f"  employee_survey   : {emp_surv.shape}")
print(f"  manager_survey    : {mgr_surv.shape}")
print(f"  in_time           : {in_time.shape}")
print(f"  out_time          : {out_time.shape}")

quality_log = {}

# ─────────────────────────────────────────────────────────────
# 2. MISSING VALUE HANDLING
# ─────────────────────────────────────────────────────────────
print("\n[2/8] Handling missing values...")
before_missing = general.isnull().sum().sum()
quality_log['initial_rows'] = len(general)
quality_log['initial_cols'] = len(general.columns)
quality_log['missing_before'] = int(before_missing)

# Impute with median (numeric columns with missing values)
for col in ['NumCompaniesWorked', 'TotalWorkingYears']:
    median_val = general[col].median()
    missing_count = general[col].isnull().sum()
    general[col].fillna(median_val, inplace=True)
    print(f"  Filled {missing_count} missing in '{col}' with median={median_val}")

quality_log['missing_after'] = int(general.isnull().sum().sum())

# ─────────────────────────────────────────────────────────────
# 3. DUPLICATE REMOVAL
# ─────────────────────────────────────────────────────────────
print("\n[3/8] Removing duplicates...")
dupes = general.duplicated().sum()
quality_log['duplicates_removed'] = int(dupes)
general.drop_duplicates(inplace=True)
print(f"  Removed {dupes} duplicate rows")

# ─────────────────────────────────────────────────────────────
# 4. DROP CONSTANT / USELESS COLUMNS
# ─────────────────────────────────────────────────────────────
print("\n[4/8] Dropping constant columns...")
drop_cols = ['EmployeeCount', 'Over18', 'StandardHours']
general.drop(columns=[c for c in drop_cols if c in general.columns], inplace=True)
print(f"  Dropped: {drop_cols}")

# ─────────────────────────────────────────────────────────────
# 5. OUTLIER DETECTION (IQR)
# ─────────────────────────────────────────────────────────────
print("\n[5/8] Detecting outliers (IQR method)...")
numeric_cols = general.select_dtypes(include=np.number).columns.tolist()
numeric_cols = [c for c in numeric_cols if c != 'EmployeeID']
outlier_report = {}
for col in numeric_cols:
    Q1 = general[col].quantile(0.25)
    Q3 = general[col].quantile(0.75)
    IQR = Q3 - Q1
    lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
    n_out = ((general[col] < lower) | (general[col] > upper)).sum()
    if n_out > 0:
        outlier_report[col] = int(n_out)
quality_log['outlier_counts'] = outlier_report
print(f"  Outlier summary: {outlier_report}")

# Cap outliers (Winsorization) instead of removing rows
for col in numeric_cols:
    Q1 = general[col].quantile(0.25)
    Q3 = general[col].quantile(0.75)
    IQR = Q3 - Q1
    general[col] = general[col].clip(Q1 - 1.5*IQR, Q3 + 1.5*IQR)

# ─────────────────────────────────────────────────────────────
# 6. FEATURE ENGINEERING
# ─────────────────────────────────────────────────────────────
print("\n[6/8] Engineering features...")

# YearsInCurrentRole (not in original, derive from YearsAtCompany)
general['YearsInCurrentRole'] = (general['YearsAtCompany'] * 0.6).astype(int).clip(0, 15)

# Synthetic EmployeeName
first_names = ['Aarav','Aditya','Akash','Amit','Ananya','Anjali','Arjun','Aryan','Deepika',
               'Dev','Divya','Gaurav','Ishaan','Karan','Kavya','Kunal','Meera','Neha',
               'Nikhil','Pooja','Priya','Rahul','Raj','Riya','Rohit','Sanjay','Sara',
               'Shivam','Sneha','Suresh','Tanvi','Varun','Vikram','Vivek','Zara',
               'James','Emily','Michael','Sarah','David','Emma','John','Olivia']
last_names  = ['Sharma','Verma','Kumar','Singh','Patel','Mehta','Gupta','Joshi','Malhotra',
               'Nair','Pillai','Rao','Reddy','Shah','Thakur','Trivedi','Agarwal',
               'Smith','Johnson','Williams','Brown','Jones','Garcia','Miller','Wilson']
rng = np.random.default_rng(42)
general['EmployeeName'] = [
    f"{rng.choice(first_names)} {rng.choice(last_names)}"
    for _ in range(len(general))
]

# Department mapping
dept_map = {
    'Sales': 1,
    'Research & Development': 2,
    'Human Resources': 3
}
general['DepartmentID'] = general['Department'].map(dept_map).fillna(1).astype(int)

# Merge survey data
merged = general.merge(emp_surv, on='EmployeeID', how='left')
merged = merged.merge(mgr_surv,  on='EmployeeID', how='left')

# PerformanceLabel: 4=High, 3=Medium; Low will be engineered
merged['PerformanceLabel'] = merged['PerformanceRating'].map({4: 'High', 3: 'Medium'})

# Engineer "Low" label based on satisfaction + involvement score
merged['satisfaction_score'] = (
    merged['EnvironmentSatisfaction'].fillna(2) +
    merged['JobSatisfaction'].fillna(2) +
    merged['WorkLifeBalance'].fillna(2) +
    merged['JobInvolvement'].fillna(2)
) / 4.0

# Bottom 10% satisfaction AND rating=3 → relabel as Low
low_mask = (
    (merged['PerformanceRating'] == 3) &
    (merged['satisfaction_score'] <= merged['satisfaction_score'].quantile(0.10))
)
merged.loc[low_mask, 'PerformanceLabel'] = 'Low'
print(f"  PerformanceLabel distribution:\n{merged['PerformanceLabel'].value_counts()}")

# ─────────────────────────────────────────────────────────────
# 7. ATTENDANCE FEATURE ENGINEERING
# ─────────────────────────────────────────────────────────────
print("\n[7/8] Processing attendance (in_time / out_time)...")
in_time.index  = in_time.index.astype(int)
out_time.index = out_time.index.astype(int)

date_cols = in_time.columns.tolist()
att_records = []

BATCH = 500
emp_ids = in_time.index.tolist()

for i, emp_id in enumerate(emp_ids):
    if i % 500 == 0:
        print(f"    Processing attendance {i}/{len(emp_ids)}...")
    row_in  = in_time.loc[emp_id]
    row_out = out_time.loc[emp_id]
    total_days = len(date_cols)
    absent = int(row_in.isna().sum())
    present_days = total_days - absent
    hours_list = []
    late_count = 0
    overtime_count = 0
    for d in date_cols:
        t_in  = row_in[d]
        t_out = row_out[d]
        if pd.notna(t_in) and pd.notna(t_out):
            try:
                dt_in  = pd.to_datetime(t_in)
                dt_out = pd.to_datetime(t_out)
                hrs = max((dt_out - dt_in).total_seconds() / 3600, 0)
                hours_list.append(hrs)
                if dt_in.hour > 9 or (dt_in.hour == 9 and dt_in.minute > 15):
                    late_count += 1
                if hrs > 9:
                    overtime_count += 1
            except:
                pass
    avg_hrs = round(np.mean(hours_list), 2) if hours_list else 0.0
    total_ot = round(sum(h - 9 for h in hours_list if h > 9), 2)
    att_records.append({
        'EmployeeID':       emp_id,
        'TotalDays':        total_days,
        'PresentDays':      present_days,
        'AbsentDays':       absent,
        'LateDays':         late_count,
        'AvgWorkingHours':  avg_hrs,
        'TotalOvertimeHrs': total_ot,
        'AttendanceRate':   round(100.0 * present_days / total_days, 2) if total_days > 0 else 0
    })

att_df = pd.DataFrame(att_records)
print(f"  Attendance records: {len(att_df)}")

# Merge attendance summary into main df
merged = merged.merge(att_df, on='EmployeeID', how='left')

# ─────────────────────────────────────────────────────────────
# 8. GENERATE SYNTHETIC TABLES
# ─────────────────────────────────────────────────────────────
print("\n[8/8] Generating synthetic tables...")

emp_ids_list = merged['EmployeeID'].tolist()

# --- ManagerSurvey (extended) ---
mgr_extended = merged[['EmployeeID', 'JobInvolvement', 'PerformanceRating']].copy()
mgr_extended['ManagerRating']      = np.clip(rng.integers(1, 6, size=len(mgr_extended)), 1, 5)
mgr_extended['LeadershipScore']    = np.round(rng.uniform(1.0, 5.0, len(mgr_extended)), 2)
mgr_extended['CommunicationScore'] = np.round(rng.uniform(1.0, 5.0, len(mgr_extended)), 2)

# --- Projects ---
project_names = [
    'CRM Revamp','AI Chatbot','ERP Migration','Mobile App Launch','Data Lake Setup',
    'Brand Refresh','HR Portal','Cloud Migration','Sales Analytics','Compliance 2025',
    'Product Redesign','Market Expansion','Cybersecurity Audit','Talent Pipeline','ESG Initiative'
]
project_types = ['Internal','External','Research','Development','Support']
projects_data = []
for pid, pname in enumerate(project_names, 1):
    start = datetime(2023, rng.integers(1,13), rng.integers(1,28))
    end   = start + timedelta(days=int(rng.integers(90, 365)))
    projects_data.append({
        'ProjectID':   pid,
        'ProjectName': pname,
        'ProjectType': rng.choice(project_types),
        'Budget':      round(float(rng.uniform(500000, 5000000)), 2),
        'StartDate':   start.strftime('%Y-%m-%d'),
        'EndDate':     end.strftime('%Y-%m-%d'),
        'Status':      rng.choice(['Active','Completed','On Hold'])
    })
projects_df = pd.DataFrame(projects_data)

# --- EmployeeProjects ---
roles = ['Lead','Developer','Analyst','QA','Designer','Manager','Coordinator']
ep_records = []
seen_pairs = set()
for emp_id in emp_ids_list:
    n_proj = int(rng.integers(1, 4))
    proj_sample = rng.choice(range(1, 16), size=n_proj, replace=False)
    for proj_id in proj_sample:
        key = (emp_id, int(proj_id))
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        ep_records.append({
            'EmployeeID':       emp_id,
            'ProjectID':        int(proj_id),
            'RoleInProject':    rng.choice(roles),
            'HoursWorked':      round(float(rng.uniform(40, 400)), 1),
            'CompletionStatus': rng.choice(['Completed','In Progress','Delayed']),
            'ProjectScore':     round(float(rng.uniform(5.0, 10.0)), 2)
        })
ep_df = pd.DataFrame(ep_records)

# --- EmployeeTraining ---
et_records = []
for emp_id in emp_ids_list:
    n_train = int(rng.integers(1, 5))
    train_sample = rng.choice(range(1, 11), size=n_train, replace=False)
    for tid in train_sample:
        status = rng.choice(['Completed','In Progress','Dropped'], p=[0.7, 0.2, 0.1])
        score  = round(float(rng.uniform(55, 100)), 2) if status == 'Completed' else 0.0
        enroll = datetime(2023, int(rng.integers(1,13)), int(rng.integers(1,28)))
        et_records.append({
            'EmployeeID':       emp_id,
            'TrainingID':       int(tid),
            'EnrollDate':       enroll.strftime('%Y-%m-%d'),
            'CompletionDate':   (enroll + timedelta(days=30)).strftime('%Y-%m-%d') if status=='Completed' else None,
            'CompletionStatus': status,
            'AssessmentScore':  score
        })
et_df = pd.DataFrame(et_records)

# --- Promotions ---
promo_records = []
promo_eligible = merged[merged['YearsSinceLastPromotion'] >= 3]['EmployeeID'].tolist()
role_progression = {
    'Sales Executive':              'Sales Manager',
    'Research Scientist':           'Senior Research Scientist',
    'Laboratory Technician':        'Senior Lab Technician',
    'Manufacturing Director':       'VP Manufacturing',
    'Healthcare Representative':    'Senior Healthcare Rep',
    'Manager':                      'Senior Manager',
    'Sales Representative':         'Sales Executive',
    'Human Resources':              'HR Manager',
    'Research Director':            'VP Research',
}
promo_id = 1
for emp_id in promo_eligible[:int(len(promo_eligible)*0.3)]:
    row = merged[merged['EmployeeID'] == emp_id].iloc[0]
    old_role = row['JobRole']
    new_role = role_progression.get(old_role, old_role + ' II')
    promo_date = datetime(2023, int(rng.integers(1,13)), int(rng.integers(1,28)))
    sal_before = int(row['MonthlyIncome'])
    sal_after  = int(sal_before * rng.uniform(1.10, 1.25))
    promo_records.append({
        'PromotionID':   promo_id,
        'EmployeeID':    emp_id,
        'PromotionDate': promo_date.strftime('%Y-%m-%d'),
        'PreviousRole':  old_role,
        'NewRole':       new_role,
        'SalaryBefore':  sal_before,
        'SalaryAfter':   sal_after,
        'Remarks':       'Performance-based promotion'
    })
    promo_id += 1
promo_df = pd.DataFrame(promo_records)

# ─────────────────────────────────────────────────────────────
# SAVE CLEANED DATA
# ─────────────────────────────────────────────────────────────
print("\n[SAVE] Exporting cleaned datasets...")

# Main employee table for DB
emp_cols = [
    'EmployeeID','EmployeeName','Age','Gender','MaritalStatus','Education','EducationField',
    'DepartmentID','JobRole','JobLevel','BusinessTravel','MonthlyIncome','PercentSalaryHike',
    'StockOptionLevel','TotalWorkingYears','TrainingTimesLastYear','YearsAtCompany',
    'YearsInCurrentRole','YearsSinceLastPromotion','YearsWithCurrManager',
    'NumCompaniesWorked','DistanceFromHome','Attrition','PerformanceRating','PerformanceLabel'
]
employees_df = merged[emp_cols].copy()

# Survey
survey_df = merged[['EmployeeID','EnvironmentSatisfaction','JobSatisfaction','WorkLifeBalance']].copy()

# ML features (all merged)
ml_cols = emp_cols + ['EnvironmentSatisfaction','JobSatisfaction','WorkLifeBalance',
                      'JobInvolvement','AvgWorkingHours','AttendanceRate','AbsentDays','LateDays',
                      'TotalOvertimeHrs','satisfaction_score']
ml_df = merged[[c for c in ml_cols if c in merged.columns]].copy()

employees_df.to_csv(os.path.join(DATA_DIR, 'employees_clean.csv'), index=False)
survey_df.to_csv(os.path.join(DATA_DIR, 'employee_survey_clean.csv'), index=False)
mgr_extended.to_csv(os.path.join(DATA_DIR, 'manager_survey_clean.csv'), index=False)
att_df.to_csv(os.path.join(DATA_DIR, 'attendance_summary.csv'), index=False)
projects_df.to_csv(os.path.join(DATA_DIR, 'projects.csv'), index=False)
ep_df.to_csv(os.path.join(DATA_DIR, 'employee_projects.csv'), index=False)
et_df.to_csv(os.path.join(DATA_DIR, 'employee_training.csv'), index=False)
promo_df.to_csv(os.path.join(DATA_DIR, 'promotions.csv'), index=False)
ml_df.to_csv(os.path.join(DATA_DIR, 'ml_features.csv'), index=False)

print(f"  employees_clean.csv      : {len(employees_df)} rows")
print(f"  employee_survey_clean.csv: {len(survey_df)} rows")
print(f"  manager_survey_clean.csv : {len(mgr_extended)} rows")
print(f"  attendance_summary.csv   : {len(att_df)} rows")
print(f"  projects.csv             : {len(projects_df)} rows")
print(f"  employee_projects.csv    : {len(ep_df)} rows")
print(f"  employee_training.csv    : {len(et_df)} rows")
print(f"  promotions.csv           : {len(promo_df)} rows")
print(f"  ml_features.csv          : {len(ml_df)} rows")

# ─────────────────────────────────────────────────────────────
# DATA QUALITY REPORT (HTML)
# ─────────────────────────────────────────────────────────────
print("\n[REPORT] Generating Data Quality Report...")

quality_log['final_rows'] = len(merged)
quality_log['perf_dist']  = merged['PerformanceLabel'].value_counts().to_dict()
quality_log['dept_dist']  = merged['Department'].value_counts().to_dict()
quality_log['attrition']  = merged['Attrition'].value_counts().to_dict()

html = f"""<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>Data Quality Report — HR Analytics</title>
<style>
  body{{font-family:'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:20px}}
  h1{{color:#38bdf8;border-bottom:2px solid #38bdf8;padding-bottom:10px}}
  h2{{color:#7dd3fc;margin-top:30px}}
  .card{{background:#1e293b;border-radius:12px;padding:20px;margin:15px 0;border-left:4px solid #38bdf8}}
  table{{width:100%;border-collapse:collapse;margin:10px 0}}
  th{{background:#0ea5e9;color:#fff;padding:10px;text-align:left}}
  td{{padding:8px 10px;border-bottom:1px solid #334155}}
  tr:hover td{{background:#1e3a5f}}
  .badge{{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:600}}
  .good{{background:#166534;color:#bbf7d0}}
  .warn{{background:#92400e;color:#fde68a}}
  .stat{{font-size:2em;font-weight:700;color:#38bdf8}}
</style>
</head>
<body>
<h1>📊 Data Quality Report — INX Future Inc. HR Analytics</h1>
<p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

<h2>Dataset Overview</h2>
<div class='card'>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Initial Rows</td><td>{quality_log['initial_rows']}</td></tr>
<tr><td>Initial Columns</td><td>{quality_log['initial_cols']}</td></tr>
<tr><td>Missing Values (Before)</td><td>{quality_log['missing_before']}</td></tr>
<tr><td>Missing Values (After)</td><td>{quality_log['missing_after']}</td></tr>
<tr><td>Duplicates Removed</td><td>{quality_log['duplicates_removed']}</td></tr>
<tr><td>Final Rows</td><td>{quality_log['final_rows']}</td></tr>
</table>
</div>

<h2>Performance Label Distribution</h2>
<div class='card'>
<table>
<tr><th>Label</th><th>Count</th><th>Percentage</th></tr>
{''.join(f"<tr><td>{k}</td><td>{v}</td><td>{100*v/quality_log['final_rows']:.1f}%</td></tr>" for k,v in quality_log['perf_dist'].items())}
</table>
</div>

<h2>Department Distribution</h2>
<div class='card'>
<table>
<tr><th>Department</th><th>Count</th><th>Percentage</th></tr>
{''.join(f"<tr><td>{k}</td><td>{v}</td><td>{100*v/quality_log['final_rows']:.1f}%</td></tr>" for k,v in quality_log['dept_dist'].items())}
</table>
</div>

<h2>Outlier Detection (IQR Method)</h2>
<div class='card'>
<table>
<tr><th>Column</th><th>Outlier Count</th><th>Action</th></tr>
{''.join(f"<tr><td>{k}</td><td>{v}</td><td><span class='badge warn'>Winsorized</span></td></tr>" for k,v in quality_log['outlier_counts'].items())}
</table>
</div>

<h2>Attrition Summary</h2>
<div class='card'>
<table>
<tr><th>Attrition</th><th>Count</th></tr>
{''.join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k,v in quality_log['attrition'].items())}
</table>
</div>

<h2>Feature Engineering Summary</h2>
<div class='card'>
<ul>
<li>✅ YearsInCurrentRole — derived from YearsAtCompany × 0.6</li>
<li>✅ EmployeeName — synthetically generated (seeded)</li>
<li>✅ DepartmentID — mapped from Department string</li>
<li>✅ PerformanceLabel — Low/Medium/High from PerformanceRating + satisfaction score</li>
<li>✅ AttendanceRate, AvgWorkingHours, LateDays, OvertimeHrs — from in_time/out_time</li>
<li>✅ satisfaction_score — composite of 4 survey metrics</li>
<li>✅ Synthetic tables: Projects (15), EmployeeProjects, EmployeeTraining, Promotions</li>
</ul>
</div>
</body></html>"""

with open(os.path.join(REPORTS, 'data_quality_report.html'), 'w', encoding='utf-8') as f:
    f.write(html)

print("\n✅ Data cleaning complete!")
print(f"   Reports  → reports/data_quality_report.html")
print(f"   Data     → data/cleaned/")
