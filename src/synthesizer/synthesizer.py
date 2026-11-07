"""
Unified Raw Data Synthesizer Engine
Scales the authentic 1,470 Kaggle IBM HR Analytics dataset into a SINGLE flat,
wide staging dataset with 100,000+ records containing all original 35 Kaggle columns
PLUS engineered SCD Type 2 historical snapshots (simulating promotions, salary increases,
department transfers, and effective date intervals).
"""

import os
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from faker import Faker

fake = Faker()
Faker.seed(42)
np.random.seed(42)
random.seed(42)

BASE_IBM_CSV = r"C:\Users\dhuke\.gemini\antigravity\scratch\enterprise-employee-warehouse\data\ibm_hr_attrition_base.csv"
OUTPUT_DIR = r"C:\Users\dhuke\.gemini\antigravity\scratch\enterprise-employee-warehouse\data"

def generate_unified_raw_staging_dataset(target_employees=100000, scd2_ratio=0.25):
    print(f"[*] Ingesting authentic Kaggle IBM HR dataset: {BASE_IBM_CSV}")
    base_df = pd.read_csv(BASE_IBM_CSV)
    print(f"[*] Base dataset contains {len(base_df):,} rows with {len(base_df.columns)} columns.")

    # Sample from 1,470 rows to target_employees
    sample_indices = np.random.choice(len(base_df), size=target_employees, replace=True)
    sampled = base_df.iloc[sample_indices].copy().reset_index(drop=True)

    all_records = []

    print(f"[*] Generating {target_employees:,} employees with engineered SCD Type 2 historical progression...")

    for emp_id in range(1, target_employees + 1):
        row = sampled.iloc[emp_id - 1].to_dict()
        
        emp_number = f"EMP-{emp_id:06d}"
        gender = row["Gender"]
        first_name = fake.first_name_male() if gender == "Male" else fake.first_name_female()
        last_name = fake.last_name()
        full_name = f"{first_name} {last_name}"
        email = f"{first_name.lower()}.{last_name.lower()}.{emp_id}@enterprise.com"

        age = int(row["Age"])
        years_at_co = min(10, max(0, int(row["YearsAtCompany"])))
        hire_year = 2026 - years_at_co
        hire_dt = datetime(hire_year, 1, 1) + timedelta(days=random.randint(0, 360))

        monthly_income = float(row["MonthlyIncome"])
        job_role = str(row["JobRole"])
        job_level = int(row["JobLevel"])
        dept = str(row["Department"])
        attrition = str(row["Attrition"])

        has_history = (random.random() < scd2_ratio) and (years_at_co >= 2)

        if not has_history:
            # Single active version
            record = dict(row)
            record["EmployeeNumber"] = emp_number
            record["EmployeeName"] = full_name
            record["Email"] = email
            record["HireDate"] = hire_dt.strftime("%Y-%m-%d")
            record["EffectiveStartDate"] = hire_dt.strftime("%Y-%m-%d")
            record["EffectiveEndDate"] = "9999-12-31"
            record["IsCurrent"] = 1
            record["RecordVersion"] = 1
            record["RecordType"] = "Current"
            all_records.append(record)
        else:
            # Engineered Historical Record (Version 1: e.g. 2 years ago prior to promotion / salary bump)
            v1_start = hire_dt
            v1_end = hire_dt + timedelta(days=random.randint(365, 750))
            v1_salary = round(monthly_income * random.uniform(0.72, 0.86), 2)
            v1_level = max(1, job_level - 1)
            v1_role = f"Associate {job_role}" if ("Senior" in job_role or "Manager" in job_role) else job_role

            v1_record = dict(row)
            v1_record["EmployeeNumber"] = emp_number
            v1_record["EmployeeName"] = full_name
            v1_record["Email"] = email
            v1_record["Age"] = max(20, age - 2)
            v1_record["JobRole"] = v1_role
            v1_record["JobLevel"] = v1_level
            v1_record["MonthlyIncome"] = v1_salary
            v1_record["YearsAtCompany"] = max(0, years_at_co - 2)
            v1_record["Attrition"] = "No"
            v1_record["HireDate"] = hire_dt.strftime("%Y-%m-%d")
            v1_record["EffectiveStartDate"] = v1_start.strftime("%Y-%m-%d")
            v1_record["EffectiveEndDate"] = v1_end.strftime("%Y-%m-%d")
            v1_record["IsCurrent"] = 0
            v1_record["RecordVersion"] = 1
            v1_record["RecordType"] = "Historical_SCD2"
            all_records.append(v1_record)

            # Current Record (Version 2: Promoted / Current State)
            v2_start = v1_end + timedelta(days=1)
            v2_record = dict(row)
            v2_record["EmployeeNumber"] = emp_number
            v2_record["EmployeeName"] = full_name
            v2_record["Email"] = email
            v2_record["HireDate"] = hire_dt.strftime("%Y-%m-%d")
            v2_record["EffectiveStartDate"] = v2_start.strftime("%Y-%m-%d")
            v2_record["EffectiveEndDate"] = "9999-12-31"
            v2_record["IsCurrent"] = 1
            v2_record["RecordVersion"] = 2
            v2_record["RecordType"] = "Current"
            all_records.append(v2_record)

    unified_df = pd.DataFrame(all_records)
    out_csv = os.path.join(OUTPUT_DIR, "stg_ibm_hr_raw.csv")
    print(f"[*] Saving unified flat dataset to {out_csv}...")
    unified_df.to_csv(out_csv, index=False)

    print(f"[OK] Single Flat Staging Dataset Created Successfully!")
    print(f"    - Unique Employees: {target_employees:,}")
    print(f"    - Total Rows (with SCD Type 2 histories): {len(unified_df):,}")
    print(f"    - Total Columns: {len(unified_df.columns)}")
    return unified_df

if __name__ == "__main__":
    generate_unified_raw_staging_dataset(target_employees=100000, scd2_ratio=0.25)
