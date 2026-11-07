-- ==============================================================================
-- Schema: enterprise_staging
-- Description: Single flat staging schema directly mirroring raw Kaggle dataset
--              scaled to 100,000+ records with engineered SCD Type 2 history
-- ==============================================================================

DROP DATABASE IF EXISTS enterprise_staging;
CREATE DATABASE enterprise_staging;
USE enterprise_staging;

CREATE TABLE IF NOT EXISTS stg_ibm_hr_raw (
    stg_id INT AUTO_INCREMENT PRIMARY KEY,
    -- Identifiers
    EmployeeNumber VARCHAR(30),
    EmployeeName VARCHAR(120),
    Email VARCHAR(120),
    HireDate DATE,
    -- Demographics & Kaggle Base Attributes
    Age INT,
    Gender VARCHAR(20),
    MaritalStatus VARCHAR(20),
    Education INT,
    EducationField VARCHAR(100),
    NumCompaniesWorked INT,
    TotalWorkingYears INT,
    YearsAtCompany INT,
    YearsInCurrentRole INT,
    YearsSinceLastPromotion INT,
    YearsWithCurrManager INT,
    -- Job & Compensation
    Department VARCHAR(100),
    JobRole VARCHAR(100),
    JobLevel INT,
    MonthlyIncome DECIMAL(12, 2),
    DailyRate INT,
    HourlyRate INT,
    MonthlyRate INT,
    PercentSalaryHike INT,
    StockOptionLevel INT,
    OverTime VARCHAR(10),
    StandardHours INT,
    Over18 VARCHAR(10),
    BusinessTravel VARCHAR(50),
    DistanceFromHome INT,
    -- Performance & Satisfaction Metrics
    PerformanceRating INT,
    JobSatisfaction INT,
    EnvironmentSatisfaction INT,
    RelationshipSatisfaction INT,
    WorkLifeBalance INT,
    JobInvolvement INT,
    TrainingTimesLastYear INT,
    -- Attrition & Status
    Attrition VARCHAR(10),
    EmployeeCount INT,
    -- Engineered SCD Type 2 Metadata Columns
    EffectiveStartDate DATE,
    EffectiveEndDate DATE,
    IsCurrent TINYINT(1),
    RecordVersion INT,
    RecordType VARCHAR(30),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_stg_emp_num (EmployeeNumber),
    INDEX idx_stg_is_curr (IsCurrent)
) ENGINE=InnoDB;
