"""
03_load_database.py
HR Analytics Platform — Load Cleaned Data into MySQL
"""

import os, sys
import pandas as pd
import numpy as np
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, 'data', 'cleaned')

DB_CONFIG = {
    'host':     os.getenv('DB_HOST',     'localhost'),
    'port':     int(os.getenv('DB_PORT', 3306)),
    'user':     os.getenv('DB_USER',     'root'),
    'password': os.getenv('DB_PASSWORD', 'root'),
    'database': os.getenv('DB_NAME',     'hr_analytics'),
    'charset':  'utf8mb4'
}

print("=" * 60)
print("  HR Analytics Platform — Database Loader")
print("=" * 60)

def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print(f"  ✅ Connected to MySQL: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
        return conn
    except Error as e:
        print(f"  ❌ Connection failed: {e}")
        sys.exit(1)

def load_table(conn, df, table_name, chunk_size=500):
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table_name}")
    conn.commit()

    cols    = df.columns.tolist()
    ph      = ', '.join(['%s'] * len(cols))
    col_str = ', '.join([f'`{c}`' for c in cols])
    sql     = f"INSERT IGNORE INTO {table_name} ({col_str}) VALUES ({ph})"

    rows_inserted = 0
    for i in range(0, len(df), chunk_size):
        chunk = df.iloc[i:i+chunk_size]
        data  = [tuple(None if (isinstance(v, float) and np.isnan(v)) else v
                       for v in row)
                 for row in chunk.values]
        try:
            cursor.executemany(sql, data)
            conn.commit()
            rows_inserted += cursor.rowcount
        except Error as e:
            print(f"    ⚠️  Error in chunk {i}: {e}")
            conn.rollback()
    cursor.close()
    print(f"  ✅ {table_name:<25} → {rows_inserted:>5} rows")
    return rows_inserted

def run_sql_file(conn, sql_path):
    with open(sql_path, 'r', encoding='utf-8') as f:
        raw = f.read()
    cursor = conn.cursor()
    for stmt in raw.split(';'):
        stmt = stmt.strip()
        if stmt and not stmt.startswith('--'):
            try:
                cursor.execute(stmt)
            except Error as e:
                if 'already exists' not in str(e).lower():
                    print(f"    SQL warn: {e}")
    conn.commit()
    cursor.close()

def main():
    # Step 1: Apply schema
    print("\n[1/3] Applying database schema...")
    schema_path = os.path.join(BASE_DIR, '01_database_setup.sql')
    conn = mysql.connector.connect(
        host=DB_CONFIG['host'], port=DB_CONFIG['port'],
        user=DB_CONFIG['user'], password=DB_CONFIG['password'],
        charset='utf8mb4'
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} "
                   f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.execute(f"USE {DB_CONFIG['database']}")
    conn.commit()
    cursor.close()
    conn.close()

    conn = get_connection()
    cursor = conn.cursor()

    # Disable FK checks during load
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    conn.commit()
    cursor.close()

    run_sql_file(conn, schema_path)
    print("  ✅ Schema applied")

    # Step 2: Load data files in FK-safe order
    print("\n[2/3] Loading data into MySQL tables...")

    # Employees
    emp_df = pd.read_csv(os.path.join(DATA_DIR, 'employees_clean.csv'))
    load_table(conn, emp_df, 'Employees')

    # EmployeeSurvey
    sur_df = pd.read_csv(os.path.join(DATA_DIR, 'employee_survey_clean.csv'))
    sur_df['SurveyDate'] = '2023-12-01'
    load_table(conn, sur_df, 'EmployeeSurvey')

    # ManagerSurvey
    mgr_df = pd.read_csv(os.path.join(DATA_DIR, 'manager_survey_clean.csv'))
    mgr_cols = ['EmployeeID','JobInvolvement','ManagerRating','LeadershipScore','CommunicationScore']
    load_table(conn, mgr_df[mgr_cols], 'ManagerSurvey')

    # Projects
    proj_df = pd.read_csv(os.path.join(DATA_DIR, 'projects.csv'))
    load_table(conn, proj_df, 'Projects')

    # EmployeeProjects
    ep_df = pd.read_csv(os.path.join(DATA_DIR, 'employee_projects.csv'))
    # filter only valid employee IDs
    valid_ids = set(emp_df['EmployeeID'].tolist())
    ep_df = ep_df[ep_df['EmployeeID'].isin(valid_ids)]
    ep_df = ep_df.drop_duplicates(subset=['EmployeeID','ProjectID'])
    load_table(conn, ep_df, 'EmployeeProjects')

    # EmployeeTraining
    et_df = pd.read_csv(os.path.join(DATA_DIR, 'employee_training.csv'))
    et_df = et_df[et_df['EmployeeID'].isin(valid_ids)]
    # replace NaN in CompletionDate
    et_df['CompletionDate'] = et_df['CompletionDate'].where(et_df['CompletionDate'].notna(), None)
    load_table(conn, et_df, 'EmployeeTraining')

    # Promotions
    promo_df = pd.read_csv(os.path.join(DATA_DIR, 'promotions.csv'))
    promo_df = promo_df[promo_df['EmployeeID'].isin(valid_ids)]
    load_table(conn, promo_df, 'Promotions')

    # Attendance (summary rows → daily rows are too large; use summary as single row per employee)
    att_df = pd.read_csv(os.path.join(DATA_DIR, 'attendance_summary.csv'))
    att_df = att_df[att_df['EmployeeID'].isin(valid_ids)]
    # Convert summary to one attendance row per employee (aggregate)
    att_load = pd.DataFrame({
        'EmployeeID':    att_df['EmployeeID'],
        'AttendanceDate': '2023-12-31',
        'LoginTime':      None,
        'LogoutTime':     None,
        'WorkingHours':   att_df['AvgWorkingHours'],
        'OvertimeHours':  att_df['TotalOvertimeHrs'].clip(upper=999.99),
        'IsAbsent':       0,
        'IsLate':         0
    })
    load_table(conn, att_load, 'Attendance')

    # Step 3: Re-enable FK checks
    cursor = conn.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()
    cursor.close()

    # Step 4: Quick validation
    print("\n[3/3] Validating row counts...")
    cursor = conn.cursor()
    tables = ['Departments','Employees','EmployeeSurvey','ManagerSurvey',
              'Attendance','Projects','EmployeeProjects','TrainingPrograms',
              'EmployeeTraining','Promotions']
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t}")
        cnt = cursor.fetchone()[0]
        print(f"  {t:<25}: {cnt:>5} rows")
    cursor.close()
    conn.close()

    print("\n✅ Database loaded successfully!")

if __name__ == '__main__':
    main()
