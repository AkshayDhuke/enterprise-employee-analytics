"""
Single Flat Staging Table Loader
Loads stg_ibm_hr_raw.csv directly into enterprise_staging.stg_ibm_hr_raw.
"""

import os
import urllib.parse
import pandas as pd
from sqlalchemy import create_engine

MYSQL_USER = os.getenv("DB_USER", "root")
MYSQL_PASSWORD = os.getenv("DB_PASSWORD", "root@2003")
MYSQL_HOST = os.getenv("DB_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("DB_PORT", "3306")

encoded_password = urllib.parse.quote_plus(MYSQL_PASSWORD)
STAGING_URL = f"mysql+pymysql://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}:{MYSQL_PORT}/enterprise_staging"

RAW_CSV = r"C:\Users\dhuke\.gemini\antigravity\scratch\enterprise-employee-warehouse\data\stg_ibm_hr_raw.csv"

def load_single_flat_staging():
    print(f"[*] Reading raw scaled dataset: {RAW_CSV}")
    engine = create_engine(STAGING_URL)

    chunksize = 15000
    total_loaded = 0
    print("[*] Ingesting into enterprise_staging.stg_ibm_hr_raw in chunks...")
    for chunk in pd.read_csv(RAW_CSV, chunksize=chunksize):
        chunk.to_sql("stg_ibm_hr_raw", engine, if_exists="append", index=False)
        total_loaded += len(chunk)
        print(f"    Loaded {total_loaded:,} rows...")

    print(f"\n[SUCCESS] Loaded {total_loaded:,} total rows into single flat table: enterprise_staging.stg_ibm_hr_raw!")

if __name__ == "__main__":
    load_single_flat_staging()
