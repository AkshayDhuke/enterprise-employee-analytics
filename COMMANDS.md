# ==============================================================================
# Enterprise Employee Analytics & Data Warehouse System
# Complete Command & Execution Reference Log
# ==============================================================================

This log contains all commands executed across the system lifecycle:
- Database setup & MySQL execution commands
- Data synthesizer & staging loader execution
- Advanced SQL stored procedures & analytical queries
- Git branching & version control commands
- Streamlit application execution commands

---

## 1. Environment & Dependencies

### Install Required Python Libraries
```powershell
pip install pandas numpy faker sqlalchemy pymysql streamlit plotly python-dotenv altair watchdog
```

---

## 2. Phase 1: Architecture, Modeling & Single Flat Staging Dataset

### Run the Data Synthesizer
Scales the authentic Kaggle IBM HR Analytics dataset (1,470 rows) up to 100,000+ distinct employees (121,426 rows including engineered historical SCD Type 2 progression records) and saves it into `data/stg_ibm_hr_raw.csv`:
```powershell
python "C:\Users\dhuke\.gemini\antigravity\scratch\enterprise-employee-warehouse\src\synthesizer\synthesizer.py"
```

### Create the Single Flat Staging Table in MySQL
Executes `sql/00_staging_schema.sql` to create `enterprise_staging.stg_ibm_hr_raw`:
```powershell
Get-Content "C:\Users\dhuke\.gemini\antigravity\scratch\enterprise-employee-warehouse\sql\00_staging_schema.sql" | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -proot@2003
```

### Ingest the Scaled Staging Dataset into MySQL
Loads all 121,426 records in chunks directly into MySQL:
```powershell
python "C:\Users\dhuke\.gemini\antigravity\scratch\enterprise-employee-warehouse\src\etl\load_staging.py"
```

### Verify Staging Row Counts in MySQL
```sql
USE enterprise_staging;
SHOW TABLES;
SELECT 
    COUNT(*) AS total_raw_records, 
    COUNT(DISTINCT EmployeeNumber) AS distinct_employees,
    SUM(CASE WHEN IsCurrent = 0 THEN 1 ELSE 0 END) AS historical_scd2_versions,
    SUM(CASE WHEN IsCurrent = 1 THEN 1 ELSE 0 END) AS current_active_employees
FROM stg_ibm_hr_raw;
```

---

## 3. Phase 2: Advanced SQL & ETL Development

### Create Normalized OLTP Schema (3NF)
Creates `enterprise_oltp` with tables: `departments`, `employees`, `projects`, `project_assignments`, `performance_reviews`:
```powershell
Get-Content "C:\Users\dhuke\.gemini\antigravity\scratch\enterprise-employee-warehouse\sql\01_oltp_schema.sql" | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -proot@2003
```

### Create Dimensional Data Warehouse Schema (Star Schema with SCD2)
Creates `enterprise_dw` with `Dim_Date`, `Dim_Department`, `Dim_Project`, `Dim_Employee` (SCD Type 2), `Fact_PerformanceReviews`, `Fact_ProjectAllocations`:
```powershell
Get-Content "C:\Users\dhuke\.gemini\antigravity\scratch\enterprise-employee-warehouse\sql\02_olap_schema.sql" | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -proot@2003
```

### Compile ETL Stored Procedures (CTEs, Window Functions & SCD2)
Compiles `sp_populate_dim_date`, `sp_etl_staging_to_oltp`, `sp_etl_load_dimensions`, `sp_update_employee_scd2`, and fact table loaders in MySQL:
```powershell
Get-Content "C:\Users\dhuke\.gemini\antigravity\scratch\enterprise-employee-warehouse\sql\03_stored_procedures_etl.sql" | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -proot@2003
```

### Execute Full End-to-End ETL Pipeline (Python Orchestrator)
Extracts, cleans, ranks (using Window functions), normalizes into OLTP, and loads into the Star Schema warehouse:
```powershell
python "C:\Users\dhuke\.gemini\antigravity\scratch\enterprise-employee-warehouse\src\etl\etl_pipeline.py"
```

### Test Advanced Analytical SQL Queries (DENSE_RANK, LAG, NTILE)
Executes complex analytical queries on the Star Schema:
```powershell
Get-Content "C:\Users\dhuke\.gemini\antigravity\scratch\enterprise-employee-warehouse\sql\04_advanced_analytical_queries.sql" | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -proot@2003
```

---

## 4. Phase 3: Python Application Logic (OOP)

### Run Phase 3 Unit Tests (Singleton, Entities & DAL)
```powershell
python -m unittest tests/test_phase3.py
```

---

## 5. Phase 4: Streamlit UI and Interactive Dashboards

### Run Streamlit Web Application Locally
Launches the full interactive HR Management and Analytics Dashboard:
```powershell
cd "C:\Users\dhuke\.gemini\antigravity\scratch\enterprise-employee-warehouse"
python -m streamlit run app/main.py
```

---

## 6. Git Branching & Version Control Commands

### Initialize Git & Initial Phase 1 Commit
```powershell
cd "C:\Users\dhuke\.gemini\antigravity\scratch\enterprise-employee-warehouse"
git init
git checkout -b main
git add .
git commit -m "feat(phase-1): architecture, OLTP/OLAP schemas, diagrams, and scaled flat staging dataset (100k+ rows with SCD Type 2)"
```

### Create Phase 1 Feature Branch
```powershell
git checkout -b feature/database-design
git checkout main
```

### Create Phase 2 Feature Branch
```powershell
git checkout -b feature/advanced-sql-etl
```

### Check Git Status and Commit History
```powershell
git status
git log --oneline --graph --decorate
```

### Merge Phase 2 Feature Branch into Main
```powershell
git checkout main
git merge feature/advanced-sql-etl --no-edit
```


### Create Phase 3 Feature Branch & Commit
```powershell
git checkout -b feature/python-oop-backend
git add .
git commit -m "feat(phase-3): modular OOP backend with Singleton DB manager, domain entities, and DAL managers"
git push -u origin feature/python-oop-backend
```
