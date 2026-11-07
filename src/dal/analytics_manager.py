"""
Analytics Manager Class (Data Access Layer)
Executes advanced SQL analytical queries (CTEs, Window Functions: DENSE_RANK, LAG, LEAD, NTILE)
on the Star Schema Data Warehouse (enterprise_dw) for executive dashboards.
"""

from typing import List, Dict, Any, Optional
from src.dal.base_manager import BaseManager


class AnalyticsManager(BaseManager):
    """
    Interfaces directly with the enterprise_dw Star Schema.
    Wraps complex analytical queries utilizing Window Functions and CTEs for Phase 4 Streamlit Dashboards.
    """

    def get_top_performers_by_department(
        self,
        department_name: Optional[str] = None,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Executes Query 1: Top-performing employees by department using DENSE_RANK().
        Ranks employees per department and year based on performance rating, satisfaction, and salary.
        """
        dept_filter = "WHERE department_name = :dept_name" if department_name else ""
        sql = f"""
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
                {dept_filter}
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
            WHERE dept_rank <= :top_n
            ORDER BY department_name, year_num DESC, dept_rank ASC;
        """
        params = {"top_n": top_n}
        if department_name:
            params["dept_name"] = department_name

        return self.execute_query(sql, params, use_dw=True)

    def get_yoy_performance_trajectory(
        self,
        employee_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes Query 2: Year-Over-Year (YoY) Performance & Salary Trajectory using LAG().
        Computes annual rating deltas and salary growth percentages.
        """
        emp_filter = "WHERE e.employee_id = :emp_id" if employee_id else ""
        sql = f"""
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
                {emp_filter}
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
        """
        params = {"emp_id": employee_id} if employee_id else {}
        return self.execute_query(sql, params, use_dw=True)

    def get_scd2_audit_trail(
        self,
        employee_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes Query 3: SCD Type 2 Audit Trail using LEAD().
        Traces historical role promotions and salary increments across employee versions.
        """
        emp_filter = "WHERE employee_id = :emp_id" if employee_id else ""
        sql = f"""
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
            {emp_filter}
            ORDER BY employee_id, version ASC;
        """
        params = {"emp_id": employee_id} if employee_id else {}
        return self.execute_query(sql, params, use_dw=True)

    def get_attrition_risk_analysis(self) -> List[Dict[str, Any]]:
        """
        Executes Query 4: Attrition Risk Analysis & Quartile Segmentation using NTILE(4).
        Categorizes current active employees by salary quartile and sentiment risk tier.
        """
        sql = """
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
        """
        return self.execute_query(sql, use_dw=True)

    def get_resource_bottlenecks(self) -> List[Dict[str, Any]]:
        """
        Executes Query 5: Project Resource Allocation Bottlenecks & Capacity Exceeded.
        Identifies over-allocated employees committed to > 100% project bandwidth.
        """
        sql = """
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
        """
        return self.execute_query(sql, use_dw=True)

    def get_executive_kpis(self) -> Dict[str, Any]:
        """
        Calculates high-level corporate KPIs for the executive summary cards in Streamlit:
        - Total headcount
        - Average performance rating
        - Average monthly compensation
        - Total active projects and aggregate budget
        - Attrition rate
        """
        emp_kpis = self.execute_query("""
            SELECT 
                COUNT(*) AS total_headcount,
                ROUND(AVG(monthly_income), 2) AS avg_monthly_income,
                SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END) AS attrited_count
            FROM Dim_Employee
            WHERE is_current = 1;
        """, use_dw=True)

        rev_kpis = self.execute_query("""
            SELECT 
                ROUND(AVG(performance_rating), 2) AS avg_performance_rating,
                ROUND(AVG(job_satisfaction), 2) AS avg_job_satisfaction,
                ROUND(AVG(work_life_balance), 2) AS avg_work_life_balance
            FROM Fact_PerformanceReviews;
        """, use_dw=True)

        proj_kpis = self.execute_query("""
            SELECT 
                COUNT(*) AS total_projects,
                SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) AS active_projects,
                ROUND(COALESCE(SUM(budget), 0), 2) AS total_budget
            FROM Dim_Project;
        """, use_dw=True)

        headcount = emp_kpis[0]["total_headcount"] if emp_kpis else 0
        attrited = emp_kpis[0]["attrited_count"] if emp_kpis else 0
        attrition_rate = round((attrited / headcount) * 100, 2) if headcount else 0.0

        return {
            "total_headcount": headcount,
            "avg_monthly_income": emp_kpis[0]["avg_monthly_income"] if emp_kpis else 0.0,
            "attrition_rate": attrition_rate,
            "avg_performance_rating": rev_kpis[0]["avg_performance_rating"] if rev_kpis else 0.0,
            "avg_job_satisfaction": rev_kpis[0]["avg_job_satisfaction"] if rev_kpis else 0.0,
            "avg_work_life_balance": rev_kpis[0]["avg_work_life_balance"] if rev_kpis else 0.0,
            "total_projects": proj_kpis[0]["total_projects"] if proj_kpis else 0,
            "active_projects": proj_kpis[0]["active_projects"] if proj_kpis else 0,
            "total_budget": proj_kpis[0]["total_budget"] if proj_kpis else 0.0,
        }
