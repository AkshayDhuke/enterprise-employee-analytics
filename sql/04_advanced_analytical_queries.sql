-- ==============================================================================
-- File: 04_advanced_analytical_queries.sql
-- Description: Analytical queries using CTEs, Window Functions (DENSE_RANK, LAG,
--              LEAD, NTILE) for executive dashboards
-- ==============================================================================

USE enterprise_dw;

-- ==============================================================================
-- Query 1: Top-Performing Employees by Department using DENSE_RANK()
-- ==============================================================================
WITH RankedDepartmentTalent AS (
    SELECT 
        e.employee_sk,
        e.employee_number,
        e.full_name,
        d.department_name,
        e.job_role,
        f.performance_rating,
        f.job_satisfaction,
        f.monthly_income,
        dt.year_num,
        DENSE_RANK() OVER (
            PARTITION BY d.department_name, dt.year_num 
            ORDER BY f.performance_rating DESC, f.job_satisfaction DESC, f.monthly_income DESC
        ) AS dept_rank
    FROM Fact_PerformanceReviews f
    JOIN Dim_Employee e ON f.employee_sk = e.employee_sk
    JOIN Dim_Department d ON f.department_sk = d.department_sk
    JOIN Dim_Date dt ON f.review_date_key = dt.date_key
)
SELECT 
    dept_rank,
    year_num,
    department_name,
    full_name,
    job_role,
    performance_rating,
    job_satisfaction,
    monthly_income
FROM RankedDepartmentTalent
WHERE dept_rank <= 5
ORDER BY department_name, year_num DESC, dept_rank ASC;

-- ==============================================================================
-- Query 2: Year-Over-Year (YoY) Performance & Salary Trajectory using LAG()
-- ==============================================================================
WITH AnnualEmployeePerformance AS (
    SELECT 
        e.employee_id,
        e.full_name,
        d.department_name,
        dt.year_num,
        AVG(f.performance_rating) AS avg_annual_rating,
        MAX(f.monthly_income) AS annual_salary
    FROM Fact_PerformanceReviews f
    JOIN Dim_Employee e ON f.employee_sk = e.employee_sk
    JOIN Dim_Department d ON f.department_sk = d.department_sk
    JOIN Dim_Date dt ON f.review_date_key = dt.date_key
    GROUP BY e.employee_id, e.full_name, d.department_name, dt.year_num
),
PerformanceTrajectory AS (
    SELECT 
        employee_id,
        full_name,
        department_name,
        year_num,
        avg_annual_rating,
        annual_salary,
        LAG(avg_annual_rating, 1) OVER (
            PARTITION BY employee_id ORDER BY year_num ASC
        ) AS prev_year_rating,
        LAG(annual_salary, 1) OVER (
            PARTITION BY employee_id ORDER BY year_num ASC
        ) AS prev_year_salary
    FROM AnnualEmployeePerformance
)
SELECT 
    employee_id,
    full_name,
    department_name,
    year_num,
    ROUND(avg_annual_rating, 2) AS rating,
    ROUND(prev_year_rating, 2) AS prev_rating,
    ROUND(avg_annual_rating - prev_year_rating, 2) AS yoy_rating_delta,
    annual_salary,
    prev_year_salary,
    ROUND(annual_salary - prev_year_salary, 2) AS yoy_salary_increment,
    ROUND(((annual_salary - prev_year_salary) / NULLIF(prev_year_salary, 0)) * 100, 2) AS salary_growth_pct
FROM PerformanceTrajectory
ORDER BY employee_id, year_num ASC;

-- ==============================================================================
-- Query 3: SCD Type 2 Audit Trail: Employee Promotion & Salary Progression
-- ==============================================================================
SELECT 
    employee_id,
    employee_number,
    full_name,
    version,
    department_name,
    job_role,
    job_level,
    monthly_income,
    attrition,
    effective_start_date,
    effective_end_date,
    is_current,
    LEAD(monthly_income) OVER (
        PARTITION BY employee_id ORDER BY version
    ) - monthly_income AS next_raise_amount
FROM Dim_Employee
ORDER BY employee_id, version ASC;

-- ==============================================================================
-- Query 4: Attrition Risk Analysis & Quartile Segmentation using NTILE(4)
-- ==============================================================================
WITH EmployeeRiskProfile AS (
    SELECT 
        e.employee_sk,
        e.full_name,
        e.department_name,
        e.job_role,
        e.attrition,
        f.performance_rating,
        f.work_life_balance,
        f.job_satisfaction,
        f.monthly_income,
        NTILE(4) OVER (ORDER BY f.monthly_income ASC) AS salary_quartile,
        CASE 
            WHEN f.work_life_balance = 1 AND f.job_satisfaction = 1 THEN 'High Attrition Risk'
            WHEN f.work_life_balance <= 2 OR f.job_satisfaction <= 2 THEN 'Moderate Risk'
            ELSE 'Low Risk'
        END AS calculated_risk_tier
    FROM Fact_PerformanceReviews f
    JOIN Dim_Employee e ON f.employee_sk = e.employee_sk
    WHERE e.is_current = 1
)
SELECT 
    department_name,
    calculated_risk_tier,
    salary_quartile,
    COUNT(*) AS employee_count,
    ROUND(AVG(performance_rating), 2) AS avg_rating,
    ROUND(AVG(job_satisfaction), 2) AS avg_satisfaction,
    SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END) AS total_attrited
FROM EmployeeRiskProfile
GROUP BY department_name, calculated_risk_tier, salary_quartile
ORDER BY department_name, calculated_risk_tier;

-- ==============================================================================
-- Query 5: Project Resource Allocation Bottlenecks & Capacity Exceeded
-- ==============================================================================
WITH TotalStaffAllocation AS (
    SELECT 
        e.employee_sk,
        e.full_name,
        e.department_name,
        COUNT(fpa.project_sk) AS assigned_project_count,
        SUM(fpa.allocation_pct) AS total_allocation_pct
    FROM Fact_ProjectAllocations fpa
    JOIN Dim_Employee e ON fpa.employee_sk = e.employee_sk
    WHERE e.is_current = 1
    GROUP BY e.employee_sk, e.full_name, e.department_name
)
SELECT 
    full_name,
    department_name,
    assigned_project_count,
    total_allocation_pct,
    CASE 
        WHEN total_allocation_pct > 100 THEN 'OVER-ALLOCATED (Bottleneck Risk)'
        WHEN total_allocation_pct = 100 THEN 'Fully Utilized'
        ELSE 'Available Bandwidth'
    END AS capacity_status
FROM TotalStaffAllocation
ORDER BY total_allocation_pct DESC;
