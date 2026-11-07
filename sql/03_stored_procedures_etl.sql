-- ==============================================================================
-- File: 03_stored_procedures_etl.sql
-- Description: Stored procedures, SCD Type 2 merge logic, and ETL pipelines
-- ==============================================================================

USE enterprise_dw;

DELIMITER $$

-- ------------------------------------------------------------------------------
-- 1. Populate Dim_Date for a specified range (e.g. 2015 to 2030)
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
-- 2. Synchronize Dimension Tables from OLTP
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_sync_dimensions$$
CREATE PROCEDURE sp_sync_dimensions()
BEGIN
    -- Sync Departments
    INSERT INTO Dim_Department (department_id, department_name, cost_center_code, location)
    SELECT 
        d.department_id,
        d.department_name,
        d.cost_center_code,
        d.location
    FROM enterprise_oltp.departments d
    ON DUPLICATE KEY UPDATE
        department_name = VALUES(department_name),
        cost_center_code = VALUES(cost_center_code),
        location = VALUES(location);

    -- Sync Projects
    INSERT INTO Dim_Project (project_id, project_code, project_name, priority, status, budget)
    SELECT 
        p.project_id,
        p.project_code,
        p.project_name,
        p.priority,
        p.status,
        p.budget
    FROM enterprise_oltp.projects p
    ON DUPLICATE KEY UPDATE
        project_name = VALUES(project_name),
        priority = VALUES(priority),
        status = VALUES(status),
        budget = VALUES(budget);
END$$

-- ------------------------------------------------------------------------------
-- 3. SCD Type 2 Procedure: Update Employee Role, Department, or Salary
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

    -- Lookup department name
    SELECT department_name INTO v_dept_name 
    FROM enterprise_oltp.departments 
    WHERE department_id = p_new_department_id;

    -- Get current active version in Dim_Employee
    SELECT 
        department_name, job_role, job_level, monthly_income, attrition, version,
        employee_number, full_name, gender, age, education_field, years_at_company, hire_date
    INTO 
        v_curr_dept_name, v_curr_job_role, v_curr_job_level, v_curr_salary, v_curr_attrition, v_curr_version,
        v_emp_number, v_full_name, v_gender, v_age, v_education_field, v_years_at_company, v_hire_date
    FROM Dim_Employee
    WHERE employee_id = p_employee_id AND is_current = 1
    LIMIT 1;

    -- If no record in DW yet, initialize first record
    IF v_curr_version IS NULL THEN
        SELECT 
            e.employee_number, CONCAT(e.first_name, ' ', e.last_name), e.gender, e.age,
            d.department_name, e.job_role, e.job_level, e.monthly_income,
            e.education_field, e.years_at_company, e.attrition, e.hire_date
        INTO 
            v_emp_number, v_full_name, v_gender, v_age,
            v_dept_name, v_curr_job_role, v_curr_job_level, v_curr_salary,
            v_education_field, v_years_at_company, v_curr_attrition, v_hire_date
        FROM enterprise_oltp.employees e
        JOIN enterprise_oltp.departments d ON e.department_id = d.department_id
        WHERE e.employee_id = p_employee_id;

        INSERT INTO Dim_Employee (
            employee_id, employee_number, full_name, gender, age,
            department_name, job_role, job_level, monthly_income,
            education_field, years_at_company, attrition, hire_date,
            effective_start_date, effective_end_date, is_current, version
        ) VALUES (
            p_employee_id, v_emp_number, v_full_name, v_gender, v_age,
            v_dept_name, p_new_job_role, p_new_job_level, p_new_salary,
            v_education_field, v_years_at_company, p_attrition, v_hire_date,
            p_effective_date, '9999-12-31', 1, 1
        );
    ELSE
        -- Check if tracked attributes actually changed
        IF (v_curr_dept_name <> v_dept_name OR 
            v_curr_job_role <> p_new_job_role OR 
            v_curr_job_level <> p_new_job_level OR 
            v_curr_salary <> p_new_salary OR 
            v_curr_attrition <> p_attrition) THEN
            
            -- Step 1: Expire current record
            UPDATE Dim_Employee
            SET 
                effective_end_date = DATE_SUB(p_effective_date, INTERVAL 1 DAY),
                is_current = 0
            WHERE employee_id = p_employee_id AND is_current = 1;

            -- Step 2: Insert new active record (SCD2 Version + 1)
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
        END IF;
    END IF;

    -- Update OLTP employee record to reflect current state
    UPDATE enterprise_oltp.employees
    SET 
        department_id = p_new_department_id,
        job_role = p_new_job_role,
        job_level = p_new_job_level,
        monthly_income = p_new_salary,
        attrition = p_attrition,
        updated_at = CURRENT_TIMESTAMP
    WHERE employee_id = p_employee_id;

END$$

-- ------------------------------------------------------------------------------
-- 4. Fact Load: Fact_PerformanceReviews using Point-in-time Dim_Employee SK
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
    -- Join Dim_Employee on Natural Key AND review date within SCD2 effective interval
    JOIN Dim_Employee de ON pr.employee_id = de.employee_id 
         AND pr.review_date BETWEEN de.effective_start_date AND de.effective_end_date
    -- Join Dim_Department by department name
    JOIN Dim_Department dd ON de.department_name = dd.department_name
    WHERE pr.review_id NOT IN (SELECT review_id FROM Fact_PerformanceReviews);
END$$

-- ------------------------------------------------------------------------------
-- 5. Fact Load: Fact_ProjectAllocations
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
