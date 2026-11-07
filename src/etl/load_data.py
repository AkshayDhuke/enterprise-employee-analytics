"""
Database Ingestion & Staging Loader
Loads synthesized data into enterprise_oltp and synchronizes enterprise_dw.
"""

import os
import urllib.parse
import pandas as pd
from sqlalchemy import create_engine, text

MYSQL_USER = os.getenv("DB_USER", "root")
MYSQL_PASSWORD = os.getenv("DB_PASSWORD", "root@2003")
MYSQL_HOST = os.getenv("DB_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("DB_PORT", "3306")

# URL encode the password to escape special characters like '@'
encoded_password = urllib.parse.quote_plus(MYSQL_PASSWORD)

OLTP_URL = f"mysql+pymysql://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}:{MYSQL_PORT}/enterprise_oltp"
DW_URL = f"mysql+pymysql://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}:{MYSQL_PORT}/enterprise_dw"

def load_data(data_dir=r"C:\Users\dhuke\.gemini\antigravity\scratch\enterprise-employee-warehouse\data"):
    print("[*] Connecting to MySQL instances...")
    oltp_engine = create_engine(OLTP_URL)
    dw_engine = create_engine(DW_URL)

    # 1. Departments
    print("[*] Loading Departments into OLTP...")
    depts_df = pd.read_csv(os.path.join(data_dir, "departments.csv"))
    depts_df.to_sql("departments", oltp_engine, if_exists="append", index=False)

    # 2. Projects
    print("[*] Loading Projects into OLTP...")
    projects_df = pd.read_csv(os.path.join(data_dir, "projects.csv"))
    projects_df.to_sql("projects", oltp_engine, if_exists="append", index=False)

    # 3. Employees
    print("[*] Loading Employees into OLTP...")
    emp_df = pd.read_csv(os.path.join(data_dir, "employees.csv"))
    emp_df.to_sql("employees", oltp_engine, if_exists="append", index=False, chunksize=5000)

    # 4. Project Assignments
    print("[*] Loading Project Assignments into OLTP...")
    asgn_df = pd.read_csv(os.path.join(data_dir, "project_assignments.csv"))
    asgn_df.to_sql("project_assignments", oltp_engine, if_exists="append", index=False, chunksize=5000)

    # 5. Performance Reviews
    print("[*] Loading Performance Reviews into OLTP...")
    rev_df = pd.read_csv(os.path.join(data_dir, "performance_reviews.csv"))
    rev_df.to_sql("performance_reviews", oltp_engine, if_exists="append", index=False, chunksize=5000)

    # 6. Load Dim_Employee (SCD Type 2) into DW
    print("[*] Loading Dim_Employee (SCD Type 2) into DW...")
    dim_emp_df = pd.read_csv(os.path.join(data_dir, "dim_employee_scd2.csv"))
    dim_emp_df.to_sql("dim_employee", dw_engine, if_exists="append", index=False, chunksize=5000)

    # 7. Run ETL Stored Procedures in DW
    print("[*] Running DW dimension sync and fact table load procedures...")
    with dw_engine.connect() as conn:
        conn.execute(text("CALL sp_sync_dimensions();"))
        conn.commit()
        print("[*] Sync dimensions complete.")
        
        conn.execute(text("CALL sp_load_fact_performance_reviews();"))
        conn.commit()
        print("[*] Fact_PerformanceReviews loaded.")

        conn.execute(text("CALL sp_load_fact_project_allocations();"))
        conn.commit()
        print("[*] Fact_ProjectAllocations loaded.")

    print("[OK] All tables and facts populated successfully in MySQL!")

if __name__ == "__main__":
    load_data()
