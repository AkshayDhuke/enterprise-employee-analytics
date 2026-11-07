-- ==============================================================================
-- Schema: enterprise_dw & enterprise_oltp ETL Procedures
-- Description: Stored Procedures using CTEs, Window Functions, and SCD Type 2 logic
--              to extract and transform data from the single flat staging table
--              into the normalized OLTP tables and OLAP Star Schema warehouse.
-- ==============================================================================

USE enterprise_dw;

DELIMITER $$

-- ------------------------------------------------------------------------------
-- 1. Dim_Date Population Procedure (2015-01-01 to 2030-12-31)
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_populate_dim_date$$
CREATE PROCEDURE sp_populate_dim_date(IN start_date DATE, IN end_date DATE)
BEGIN
    DECLARE cur_date DATE;
    SET cur_date = start_date;

    WHILE cur_date <= end_date DO
        INSERT IGNORE INTO Dim_Date (
            date_key,
            full_date,
            day_of_month,
            day_name,
            day_of_week,
            month_num,
            month_name,
            quarter_num,
            quarter_name,
            year_num,
            is_weekend
        )
        VALUES (
            YEAR(cur_date) * 10000 + MONTH(cur_date) * 100 + DAY(cur_date),
            cur_date,
            DAY(cur_date),
            DAYNAME(cur_date),
            DAYOFWEEK(cur_date),
            MONTH(cur_date),
            MONTHNAME(cur_date),
            QUARTER(cur_date),
            CONCAT('Q', QUARTER(cur_date)),
            YEAR(cur_date),
            IF(DAYOFWEEK(cur_date) IN (1, 7), TRUE, FALSE)
        );
        SET cur_date = DATE_ADD(cur_date, INTERVAL 1 DAY);
    END WHILE;
END$$

-- ------------------------------------------------------------------------------
-- 2. ETL Procedure: Load Normalized OLTP Tables from Single Flat Staging Table
--    Uses CTEs and Window Functions (ROW_NUMBER) to extract, deduplicate, and normalize
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_etl_staging_to_oltp$$
CREATE PROCEDURE sp_etl_staging_to_oltp()
BEGIN
    -- 2.1 Seed Normalized Departments from Staging
    INSERT INTO enterprise_oltp.departments (department_name, cost_center_code, location)
    SELECT DISTINCT 
        Department AS department_name,
        CASE 
            WHEN Department = 'Research & Development' THEN 'CC-RND-101'
            WHEN Department = 'Sales' THEN 'CC-SLS-202'
            WHEN Department = 'Human Resources' THEN 'CC-HR-303'
            ELSE CONCAT('CC-', UPPER(LEFT(Department, 3)), '-001')
        END AS cost_center_code,
        CASE 
            WHEN Department = 'Research & Development' THEN 'Building A - Tech Park'
            WHEN Department = 'Sales' THEN 'Building B - Corporate Tower'
            ELSE 'Building C - Exec Center'
        END AS location
    FROM enterprise_staging.stg_ibm_hr_raw
    WHERE Department IS NOT NULL
    ON DUPLICATE KEY UPDATE department_name = VALUES(department_name);

    -- 2.2 Populate Default Enterprise Projects if not present
    INSERT IGNORE INTO enterprise_oltp.projects (project_id, project_code, project_name, department_id, priority, status, start_date, budget)
    VALUES 
    (1, 'PRJ-01-0001', 'Cloud Migration & Modernization', 1, 'Critical', 'Active', '2023-01-15', 1250000.00),
    (2, 'PRJ-01-0002', 'NextGen AI & ML Pipeline', 1, 'High', 'Active', '2023-03-01', 850000.00),
    (3, 'PRJ-02-0001', 'Global Sales CRM Expansion', 2, 'High', 'Active', '2023-02-10', 600000.00),
    (4, 'PRJ-02-0002', 'Enterprise E-Commerce Portal', 2, 'Medium', 'Active', '2023-04-01', 450000.00),
    (5, 'PRJ-03-0001', 'HR Workday & Talent Automation', 3, 'Medium', 'Active', '2023-05-15', 350000.00),
    (6, 'PRJ-01-0003', 'Cybersecurity & Zero Trust Hardening', 1, 'Critical', 'Active', '2023-06-01', 950000.00);

    -- 2.3 Populate Employees in OLTP (Current active records only)
    -- Uses CTE and Window Function ROW_NUMBER() to ensure exactly 1 latest active record per employee
    INSERT INTO enterprise_oltp.employees (
        employee_number,
        first_name,
        last_name,
        email,
        gender,
        age,
        department_id,
        job_role,
        job_level,
        monthly_income,
        education_field,
        years_at_company,
        attrition,
        hire_date
    )
    WITH RankedActiveEmployees AS (
        SELECT 
            s.EmployeeNumber,
            SUBSTRING_INDEX(s.EmployeeName, ' ', 1) AS first_name,
            SUBSTRING_INDEX(s.EmployeeName, ' ', -1) AS last_name,
            s.Email,
            s.Gender,
            s.Age,
            d.department_id,
            s.JobRole,
            s.JobLevel,
            s.MonthlyIncome,
            s.EducationField,
            s.YearsAtCompany,
            s.Attrition,
            s.HireDate,
            ROW_NUMBER() OVER (
                PARTITION BY s.EmployeeNumber 
                ORDER BY s.RecordVersion DESC, s.EffectiveStartDate DESC
            ) AS rn
        FROM enterprise_staging.stg_ibm_hr_raw s
        JOIN enterprise_oltp.departments d ON s.Department = d.department_name
        WHERE s.IsCurrent = 1
    )
    SELECT 
        EmployeeNumber, first_name, last_name, Email, Gender, Age,
        department_id, JobRole, JobLevel, MonthlyIncome, EducationField,
        YearsAtCompany, Attrition, HireDate
    FROM RankedActiveEmployees
    WHERE rn = 1
    ON DUPLICATE KEY UPDATE
        monthly_income = VALUES(monthly_income),
        job_role = VALUES(job_role),
        job_level = VALUES(job_level),
        department_id = VALUES(department_id),
        attrition = VALUES(attrition);

    -- 2.4 Populate Performance Reviews in OLTP
    -- Uses CTE to generate realistic ratings and satisfaction scores based on raw staging indicators
    INSERT INTO enterprise_oltp.performance_reviews (
        employee_id,
        review_date,
        review_cycle,
        performance_rating,
        work_life_balance,
        job_satisfaction,
        training_times_last_year,
        reviewer_comments
    )
    WITH CleanedReviews AS (
        SELECT 
            e.employee_id,
            s.EffectiveStartDate AS review_date,
            CONCAT(YEAR(s.EffectiveStartDate), '-Q', QUARTER(s.EffectiveStartDate)) AS review_cycle,
            s.PerformanceRating,
            s.WorkLifeBalance,
            s.JobSatisfaction,
            s.TrainingTimesLastYear,
            CONCAT('Standard performance review. Job involvement score: ', s.JobInvolvement, '/4.') AS comments,
            ROW_NUMBER() OVER (
                PARTITION BY e.employee_id, s.EffectiveStartDate 
                ORDER BY s.stg_id ASC
            ) AS rn
        FROM enterprise_staging.stg_ibm_hr_raw s
        JOIN enterprise_oltp.employees e ON s.EmployeeNumber = e.employee_number
    )
    SELECT 
        employee_id, review_date, review_cycle, PerformanceRating,
        WorkLifeBalance, JobSatisfaction, TrainingTimesLastYear, comments
    FROM CleanedReviews
    WHERE rn = 1;

    -- 2.5 Populate Default Project Assignments in OLTP
    -- Maps employees to active projects according to their department
    INSERT INTO enterprise_oltp.project_assignments (
        employee_id,
        project_id,
        assigned_role,
        allocation_pct,
        assigned_date
    )
    SELECT 
        e.employee_id,
        p.project_id,
        e.job_role,
        CASE 
            WHEN MOD(e.employee_id, 3) = 0 THEN 100
            WHEN MOD(e.employee_id, 3) = 1 THEN 50
            ELSE 75
        END AS allocation_pct,
        e.hire_date AS assigned_date
    FROM enterprise_oltp.employees e
    JOIN enterprise_oltp.projects p ON e.department_id = p.department_id
    WHERE e.employee_id <= 10000; -- Initial active workload cohort
END$$

-- ------------------------------------------------------------------------------
-- 3. ETL Procedure: Load Dimension Tables in enterprise_dw (Star Schema)
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_etl_load_dimensions$$
CREATE PROCEDURE sp_etl_load_dimensions()
BEGIN
    -- 3.1 Load Dim_Department
    INSERT INTO Dim_Department (department_id, department_name, cost_center_code, location)
    SELECT 
        department_id, department_name, cost_center_code, location
    FROM enterprise_oltp.departments
    ON DUPLICATE KEY UPDATE
        department_name = VALUES(department_name),
        cost_center_code = VALUES(cost_center_code),
        location = VALUES(location);

    -- 3.2 Load Dim_Project
    INSERT INTO Dim_Project (project_id, project_code, project_name, priority, status, budget)
    SELECT 
        project_id, project_code, project_name, priority, status, budget
    FROM enterprise_oltp.projects
    ON DUPLICATE KEY UPDATE
        project_name = VALUES(project_name),
        priority = VALUES(priority),
        status = VALUES(status),
        budget = VALUES(budget);

    -- 3.3 Load Dim_Employee (SCD Type 2) from Single Flat Staging Table
    -- Preserves full temporal version history (Version 1 historical + Version 2 active)
    INSERT INTO Dim_Employee (
        employee_id,
        employee_number,
        full_name,
        gender,
        age,
        department_name,
        job_role,
        job_level,
        monthly_income,
        education_field,
        years_at_company,
        attrition,
        hire_date,
        effective_start_date,
        effective_end_date,
        is_current,
        version
    )
    SELECT 
        e.employee_id,
        s.EmployeeNumber,
        s.EmployeeName,
        s.Gender,
        s.Age,
        s.Department,
        s.JobRole,
        s.JobLevel,
        s.MonthlyIncome,
        s.EducationField,
        s.YearsAtCompany,
        s.Attrition,
        s.HireDate,
        s.EffectiveStartDate,
        s.EffectiveEndDate,
        s.IsCurrent,
        s.RecordVersion
    FROM enterprise_staging.stg_ibm_hr_raw s
    JOIN enterprise_oltp.employees e ON s.EmployeeNumber = e.employee_number
    ORDER BY e.employee_id, s.RecordVersion ASC;
END$$

-- ------------------------------------------------------------------------------
-- 4. SCD Type 2 Procedure: Update Employee Role / Department / Salary
--    Properly expires current active record (is_current=0, effective_end_date=p_effective_date - 1)
--    and inserts new version (is_current=1, effective_end_date='9999-12-31', version=version+1)
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_update_employee_scd2$$
CREATE PROCEDURE sp_update_employee_scd2(
    IN p_employee_id INT,
    IN p_new_department_id INT,
    IN p_new_job_role VARCHAR(100),
    IN p_new_job_level INT,
    IN p_new_salary DECIMAL(12, 2),
    IN p_attrition VARCHAR(10),
    IN p_effective_date DATE
)
BEGIN
    DECLARE v_dept_name VARCHAR(100);
    DECLARE v_curr_dept_name VARCHAR(100);
    DECLARE v_curr_job_role VARCHAR(100);
    DECLARE v_curr_job_level INT;
    DECLARE v_curr_salary DECIMAL(12, 2);
    DECLARE v_curr_attrition VARCHAR(10);
    DECLARE v_curr_version INT;
    DECLARE v_emp_number VARCHAR(20);
    DECLARE v_full_name VARCHAR(120);
    DECLARE v_gender VARCHAR(20);
    DECLARE v_age INT;
    DECLARE v_education_field VARCHAR(100);
    DECLARE v_years_at_company INT;
    DECLARE v_hire_date DATE;

    -- Lookup new department name
    SELECT department_name INTO v_dept_name 
    FROM enterprise_oltp.departments 
    WHERE department_id = p_new_department_id;

    -- Fetch current active version in Dim_Employee
    SELECT 
        department_name, job_role, job_level, monthly_income, attrition, version,
        employee_number, full_name, gender, age, education_field, years_at_company, hire_date
    INTO 
        v_curr_dept_name, v_curr_job_role, v_curr_job_level, v_curr_salary, v_curr_attrition, v_curr_version,
        v_emp_number, v_full_name, v_gender, v_age, v_education_field, v_years_at_company, v_hire_date
    FROM Dim_Employee
    WHERE employee_id = p_employee_id AND is_current = 1
    LIMIT 1;

    -- Check if tracked attributes actually changed
    IF (v_curr_dept_name <> v_dept_name OR 
        v_curr_job_role <> p_new_job_role OR 
        v_curr_job_level <> p_new_job_level OR 
        v_curr_salary <> p_new_salary OR 
        v_curr_attrition <> p_attrition) THEN
        
        -- Step 1: Expire current active version
        UPDATE Dim_Employee
        SET 
            effective_end_date = DATE_SUB(p_effective_date, INTERVAL 1 DAY),
            is_current = 0
        WHERE employee_id = p_employee_id AND is_current = 1;

        -- Step 2: Insert new active record with incremented version
        INSERT INTO Dim_Employee (
            employee_id, employee_number, full_name, gender, age,
            department_name, job_role, job_level, monthly_income,
            education_field, years_at_company, attrition, hire_date,
            effective_start_date, effective_end_date, is_current, version
        ) VALUES (
            p_employee_id, v_emp_number, v_full_name, v_gender, v_age,
            v_dept_name, p_new_job_role, p_new_job_level, p_new_salary,
            v_education_field, v_years_at_company, p_attrition, v_hire_date,
            p_effective_date, '9999-12-31', 1, v_curr_version + 1
        );

        -- Step 3: Synchronize current state in OLTP
        UPDATE enterprise_oltp.employees
        SET 
            department_id = p_new_department_id,
            job_role = p_new_job_role,
            job_level = p_new_job_level,
            monthly_income = p_new_salary,
            attrition = p_attrition,
            updated_at = CURRENT_TIMESTAMP
        WHERE employee_id = p_employee_id;
    END IF;
END$$

-- ------------------------------------------------------------------------------
-- 5. ETL Procedure: Load Fact_PerformanceReviews (Star Schema Fact)
--    Performs point-in-time join matching review date within SCD2 validity interval
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_load_fact_performance_reviews$$
CREATE PROCEDURE sp_load_fact_performance_reviews()
BEGIN
    INSERT INTO Fact_PerformanceReviews (
        review_id,
        employee_sk,
        department_sk,
        review_date_key,
        performance_rating,
        work_life_balance,
        job_satisfaction,
        training_times_last_year,
        monthly_income
    )
    SELECT 
        pr.review_id,
        de.employee_sk,
        dd.department_sk,
        YEAR(pr.review_date) * 10000 + MONTH(pr.review_date) * 100 + DAY(pr.review_date) AS review_date_key,
        pr.performance_rating,
        pr.work_life_balance,
        pr.job_satisfaction,
        pr.training_times_last_year,
        de.monthly_income
    FROM enterprise_oltp.performance_reviews pr
    JOIN enterprise_oltp.employees e ON pr.employee_id = e.employee_id
    -- Point-in-time join with Dim_Employee SCD2
    JOIN Dim_Employee de ON pr.employee_id = de.employee_id 
         AND pr.review_date BETWEEN de.effective_start_date AND de.effective_end_date
    JOIN Dim_Department dd ON de.department_name = dd.department_name
    WHERE pr.review_id NOT IN (SELECT review_id FROM Fact_PerformanceReviews);
END$$

-- ------------------------------------------------------------------------------
-- 6. ETL Procedure: Load Fact_ProjectAllocations
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_load_fact_project_allocations$$
CREATE PROCEDURE sp_load_fact_project_allocations()
BEGIN
    INSERT INTO Fact_ProjectAllocations (
        assignment_id,
        employee_sk,
        project_sk,
        assigned_date_key,
        allocation_pct,
        assigned_role
    )
    SELECT 
        pa.assignment_id,
        de.employee_sk,
        dp.project_sk,
        YEAR(pa.assigned_date) * 10000 + MONTH(pa.assigned_date) * 100 + DAY(pa.assigned_date) AS assigned_date_key,
        pa.allocation_pct,
        pa.assigned_role
    FROM enterprise_oltp.project_assignments pa
    JOIN enterprise_oltp.employees e ON pa.employee_id = e.employee_id
    JOIN Dim_Employee de ON pa.employee_id = de.employee_id 
         AND pa.assigned_date BETWEEN de.effective_start_date AND de.effective_end_date
    JOIN Dim_Project dp ON pa.project_id = dp.project_id
    WHERE pa.assignment_id NOT IN (SELECT assignment_id FROM Fact_ProjectAllocations);
END$$

DELIMITER ;
