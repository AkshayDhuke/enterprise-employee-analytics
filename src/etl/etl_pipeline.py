"""
Phase 2 ETL Pipeline Orchestrator
Executes end-to-end extraction from the single flat staging table,
transforms and normalizes data into enterprise_oltp, and loads
the dimensional Star Schema in enterprise_dw with SCD Type 2 handling.
"""

import os
import urllib.parse
from sqlalchemy import create_engine, text

MYSQL_USER = os.getenv("DB_USER", "root")
MYSQL_PASSWORD = os.getenv("DB_PASSWORD", "root@2003")
MYSQL_HOST = os.getenv("DB_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("DB_PORT", "3306")

encoded_password = urllib.parse.quote_plus(MYSQL_PASSWORD)
DW_URL = f"mysql+pymysql://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}:{MYSQL_PORT}/enterprise_dw"
OLTP_URL = f"mysql+pymysql://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}:{MYSQL_PORT}/enterprise_oltp"

def run_etl_pipeline():
    print("=" * 70)
    print("STARTING PHASE 2 ENTERPRISE ETL PIPELINE")
    print("=" * 70)

    dw_engine = create_engine(DW_URL)
    oltp_engine = create_engine(OLTP_URL)

    with dw_engine.connect() as conn:
        # Step 1: Dim_Date Generation
        print("\n[Step 1/5] Populating Dim_Date dimension (2015 to 2030)...")
        conn.execute(text("CALL sp_populate_dim_date('2015-01-01', '2030-12-31');"))
        conn.commit()
        date_cnt = conn.execute(text("SELECT COUNT(*) FROM Dim_Date;")).scalar()
        print(f"    -> Dim_Date active rows: {date_cnt:,}")

        # Step 2: Staging -> OLTP Normalization using CTEs & Window Functions
        print("\n[Step 2/5] Running sp_etl_staging_to_oltp (CTEs & ROW_NUMBER deduplication)...")
        conn.execute(text("CALL sp_etl_staging_to_oltp();"))
        conn.commit()

    with oltp_engine.connect() as oltp_conn:
        emp_cnt = oltp_conn.execute(text("SELECT COUNT(*) FROM employees;")).scalar()
        dept_cnt = oltp_conn.execute(text("SELECT COUNT(*) FROM departments;")).scalar()
        proj_cnt = oltp_conn.execute(text("SELECT COUNT(*) FROM projects;")).scalar()
        rev_cnt = oltp_conn.execute(text("SELECT COUNT(*) FROM performance_reviews;")).scalar()
        asgn_cnt = oltp_conn.execute(text("SELECT COUNT(*) FROM project_assignments;")).scalar()
        print(f"    -> Normalized OLTP Employees: {emp_cnt:,}")
        print(f"    -> Normalized OLTP Departments: {dept_cnt:,}")
        print(f"    -> Normalized OLTP Projects: {proj_cnt:,}")
        print(f"    -> Normalized OLTP Reviews: {rev_cnt:,}")
        print(f"    -> Normalized OLTP Assignments: {asgn_cnt:,}")

    with dw_engine.connect() as conn:
        # Step 3: Load Dimensions (Dim_Department, Dim_Project, Dim_Employee SCD2)
        print("\n[Step 3/5] Loading Dimension Tables in Data Warehouse (Dim_Employee SCD Type 2)...")
        conn.execute(text("CALL sp_etl_load_dimensions();"))
        conn.commit()
        dim_emp_cnt = conn.execute(text("SELECT COUNT(*) FROM Dim_Employee;")).scalar()
        hist_cnt = conn.execute(text("SELECT COUNT(*) FROM Dim_Employee WHERE is_current = 0;")).scalar()
        curr_cnt = conn.execute(text("SELECT COUNT(*) FROM Dim_Employee WHERE is_current = 1;")).scalar()
        print(f"    -> Dim_Employee Total Versions: {dim_emp_cnt:,}")
        print(f"       - Current Active Records: {curr_cnt:,}")
        print(f"       - Historical SCD2 Past Versions: {hist_cnt:,}")

        # Step 4: Load Fact_PerformanceReviews (Point-in-time joins)
        print("\n[Step 4/5] Loading Fact_PerformanceReviews (Point-in-Time Dimension joins)...")
        conn.execute(text("CALL sp_load_fact_performance_reviews();"))
        conn.commit()
        fact_rev_cnt = conn.execute(text("SELECT COUNT(*) FROM Fact_PerformanceReviews;")).scalar()
        print(f"    -> Fact_PerformanceReviews rows: {fact_rev_cnt:,}")

        # Step 5: Load Fact_ProjectAllocations
        print("\n[Step 5/5] Loading Fact_ProjectAllocations...")
        conn.execute(text("CALL sp_load_fact_project_allocations();"))
        conn.commit()
        fact_alloc_cnt = conn.execute(text("SELECT COUNT(*) FROM Fact_ProjectAllocations;")).scalar()
        print(f"    -> Fact_ProjectAllocations rows: {fact_alloc_cnt:,}")

    print("\n" + "=" * 70)
    print("PHASE 2 ETL PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_etl_pipeline()
