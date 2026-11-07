-- ==============================================================================
-- Schema: enterprise_dw
-- Description: Star Schema Dimensional Data Warehouse with SCD Type 2
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS enterprise_dw;
USE enterprise_dw;

-- ==============================================================================
-- 1. Dimension Tables
-- ==============================================================================

-- 1.1 Dim_Date (Role-playing date dimension)
CREATE TABLE IF NOT EXISTS Dim_Date (
    date_key INT PRIMARY KEY,              -- Format: YYYYMMDD (e.g. 20241015)
    full_date DATE NOT NULL UNIQUE,
    day_of_month TINYINT NOT NULL,
    day_name VARCHAR(15) NOT NULL,
    day_of_week TINYINT NOT NULL,
    month_num TINYINT NOT NULL,
    month_name VARCHAR(15) NOT NULL,
    quarter_num TINYINT NOT NULL,
    quarter_name VARCHAR(10) NOT NULL,     -- e.g. 'Q1'
    year_num SMALLINT NOT NULL,
    is_weekend BOOLEAN NOT NULL DEFAULT FALSE
) ENGINE=InnoDB;

-- 1.2 Dim_Department
CREATE TABLE IF NOT EXISTS Dim_Department (
    department_sk INT AUTO_INCREMENT PRIMARY KEY, -- Surrogate Key
    department_id INT NOT NULL,                  -- Natural Key from OLTP
    department_name VARCHAR(100) NOT NULL,
    cost_center_code VARCHAR(50) NOT NULL,
    location VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_dept_nk (department_id)
) ENGINE=InnoDB;

-- 1.3 Dim_Project
CREATE TABLE IF NOT EXISTS Dim_Project (
    project_sk INT AUTO_INCREMENT PRIMARY KEY,   -- Surrogate Key
    project_id INT NOT NULL,                     -- Natural Key from OLTP
    project_code VARCHAR(20) NOT NULL,
    project_name VARCHAR(150) NOT NULL,
    priority VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    budget DECIMAL(15, 2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_proj_nk (project_id)
) ENGINE=InnoDB;

-- 1.4 Dim_Employee (SCD Type 2: Slowly Changing Dimension)
CREATE TABLE IF NOT EXISTS Dim_Employee (
    employee_sk INT AUTO_INCREMENT PRIMARY KEY,  -- Surrogate Key (each version gets a new SK)
    employee_id INT NOT NULL,                    -- Natural Key from OLTP
    employee_number VARCHAR(20) NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    gender VARCHAR(20),
    age INT,
    department_name VARCHAR(100) NOT NULL,       -- Tracked attribute for SCD2
    job_role VARCHAR(100) NOT NULL,              -- Tracked attribute for SCD2
    job_level INT NOT NULL,                      -- Tracked attribute for SCD2
    monthly_income DECIMAL(12, 2) NOT NULL,      -- Tracked attribute for SCD2
    education_field VARCHAR(100),
    years_at_company INT,
    attrition VARCHAR(10) NOT NULL DEFAULT 'No', -- Tracked attribute for SCD2
    hire_date DATE NOT NULL,
    -- SCD Type 2 Metadata Columns
    effective_start_date DATE NOT NULL,
    effective_end_date DATE NOT NULL DEFAULT '9999-12-31',
    is_current TINYINT(1) NOT NULL DEFAULT 1,    -- 1 = Current record, 0 = Historical record
    version INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_dim_emp_nk (employee_id),
    INDEX idx_dim_emp_current (is_current),
    INDEX idx_dim_emp_eff (effective_start_date, effective_end_date)
) ENGINE=InnoDB;

-- ==============================================================================
-- 2. Fact Tables
-- ==============================================================================

-- 2.1 Fact_PerformanceReviews (Star Schema Fact)
CREATE TABLE IF NOT EXISTS Fact_PerformanceReviews (
    fact_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    review_id INT NOT NULL,                      -- Degenerate dimension / transaction key
    employee_sk INT NOT NULL,                    -- FK to Dim_Employee (Point-in-time accurate)
    department_sk INT NOT NULL,                  -- FK to Dim_Department
    review_date_key INT NOT NULL,                -- FK to Dim_Date
    performance_rating INT NOT NULL,             -- Metric: 1 to 5
    work_life_balance INT NOT NULL,              -- Metric: 1 to 4
    job_satisfaction INT NOT NULL,               -- Metric: 1 to 4
    training_times_last_year INT DEFAULT 0,      -- Metric
    monthly_income DECIMAL(12, 2) NOT NULL,      -- Metric snapshot
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_fact_emp FOREIGN KEY (employee_sk) REFERENCES Dim_Employee(employee_sk),
    CONSTRAINT fk_fact_dept FOREIGN KEY (department_sk) REFERENCES Dim_Department(department_sk),
    CONSTRAINT fk_fact_date FOREIGN KEY (review_date_key) REFERENCES Dim_Date(date_key)
) ENGINE=InnoDB;

-- 2.2 Fact_ProjectAllocations (Tracking project workload & staffing metrics)
CREATE TABLE IF NOT EXISTS Fact_ProjectAllocations (
    allocation_fact_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    assignment_id INT NOT NULL,
    employee_sk INT NOT NULL,
    project_sk INT NOT NULL,
    assigned_date_key INT NOT NULL,
    allocation_pct INT NOT NULL,                 -- Metric: % commitment
    assigned_role VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_fact_alloc_emp FOREIGN KEY (employee_sk) REFERENCES Dim_Employee(employee_sk),
    CONSTRAINT fk_fact_alloc_proj FOREIGN KEY (project_sk) REFERENCES Dim_Project(project_sk),
    CONSTRAINT fk_fact_alloc_date FOREIGN KEY (assigned_date_key) REFERENCES Dim_Date(date_key)
) ENGINE=InnoDB;

-- Analytics Indexes
CREATE INDEX idx_fact_rev_metrics ON Fact_PerformanceReviews(performance_rating, job_satisfaction);
CREATE INDEX idx_fact_alloc_load ON Fact_ProjectAllocations(project_sk, allocation_pct);
