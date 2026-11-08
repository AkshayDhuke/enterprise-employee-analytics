"""
Advanced Analytical Engine View.
Interactive presentation of Phase 2 Advanced SQL queries utilizing Window Functions
(DENSE_RANK, LAG, LEAD, NTILE) and Common Table Expressions (CTEs) on the Star Schema Data Warehouse.
"""

import streamlit as st
import pandas as pd

from app.data_provider import DataProvider
from app.utils.ui_helpers import render_section_header
from app.utils.charts import (
    plot_top_performers,
    plot_yoy_trajectory,
    plot_scd2_timeline,
    plot_attrition_risk_quartiles,
    plot_resource_bottlenecks,
)


def render_analytics_hub_view(provider: DataProvider):
    """Renders the 5 Advanced SQL Analytical queries."""
    st.title("⚡ Advanced SQL Analytical Engine")
    st.markdown(
        "Executive business intelligence powered by SQL Window Functions, CTEs, and dimensional star schema aggregation."
    )

    tabs = st.tabs([
        "🏆 Top Talent (DENSE_RANK)",
        "📈 YoY Trajectory (LAG)",
        "🕰️ SCD Type 2 Audit (LEAD)",
        "⚠️ Attrition Risk (NTILE 4)",
        "🚨 Resource Bottlenecks",
    ])

    # -------------------------------------------------------------------------
    # TAB 1: Top Talent using DENSE_RANK()
    # -------------------------------------------------------------------------
    with tabs[0]:
        render_section_header("Query 1: Top Performers Ranked by Department", "Uses DENSE_RANK() partitioned by department and year.")

        col1, col2 = st.columns([2, 1])
        with col1:
            dept_filter = st.selectbox(
                "Filter Department:",
                ["All", "Engineering & IT", "Research & Development", "Sales", "Finance & Operations", "Human Resources"],
                key="dense_rank_dept",
            )
        with col2:
            top_n = st.slider("Select Top N Ranks:", min_value=1, max_value=10, value=5, key="dense_rank_slider")

        top_df = provider.get_top_performers(department_name=None if dept_filter == "All" else dept_filter, top_n=top_n)

        if not top_df.empty:
            st.plotly_chart(plot_top_performers(top_df), use_container_width=True)

            display_table = top_df.copy()
            display_table["monthly_income"] = display_table["monthly_income"].apply(lambda x: f"${x:,.2f}")
            display_table.columns = ["Rank", "Year", "Department", "Employee", "Role", "Rating", "Satisfaction", "Monthly Income"]
            st.dataframe(display_table, use_container_width=True, hide_index=True)
        else:
            st.info("No records matching the selected department filter.")

        with st.expander("🔍 View Underlying Advanced SQL Query (CTEs & DENSE_RANK)"):
            st.code(
                """
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
SELECT dept_rank, year_num, department_name, full_name, job_role, performance_rating, job_satisfaction, monthly_income
FROM RankedDepartmentTalent
WHERE dept_rank <= :top_n
ORDER BY department_name, year_num DESC, dept_rank ASC;
                """,
                language="sql",
            )

    # -------------------------------------------------------------------------
    # TAB 2: YoY Performance Trajectory using LAG()
    # -------------------------------------------------------------------------
    with tabs[1]:
        render_section_header("Query 2: Year-Over-Year Performance & Compensation Trajectory", "Uses LAG() to compute annual performance rating deltas and salary growth %.")

        emp_list = provider.get_all_employees(limit=20)
        emp_options = {e["employee_id"]: f"{e['full_name']} ({e['job_role']})" for e in emp_list}
        
        selected_emp_id = st.selectbox(
            "Select Employee to Analyze Trajectory:",
            options=list(emp_options.keys()),
            format_func=lambda x: emp_options.get(x, str(x)),
            key="lag_emp_select",
        )

        selected_name = emp_options.get(selected_emp_id, "Selected Employee").split(" (")[0]
        yoy_df = provider.get_yoy_trajectory(selected_emp_id)

        if not yoy_df.empty:
            st.plotly_chart(plot_yoy_trajectory(yoy_df, selected_name), use_container_width=True)

            yoy_display = yoy_df.copy()
            yoy_display["annual_salary"] = yoy_display["annual_salary"].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "-")
            yoy_display["prev_year_salary"] = yoy_display["prev_year_salary"].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "-")
            yoy_display["yoy_salary_increment"] = yoy_display["yoy_salary_increment"].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "-")
            yoy_display["salary_growth_pct"] = yoy_display["salary_growth_pct"].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")

            cols_to_show = ["year_num", "department_name", "rating", "prev_rating", "yoy_rating_delta", "annual_salary", "prev_year_salary", "yoy_salary_increment", "salary_growth_pct"]
            yoy_display = yoy_display[cols_to_show]
            yoy_display.columns = ["Year", "Department", "Rating", "Prev Rating", "Rating Delta", "Salary", "Prev Salary", "Salary Increment", "Growth %"]
            st.dataframe(yoy_display, use_container_width=True, hide_index=True)
        else:
            st.info(f"No multi-year evaluation history found for employee #{selected_emp_id}.")

        with st.expander("🔍 View Underlying Advanced SQL Query (CTEs & LAG)"):
            st.code(
                """
WITH AnnualEmployeePerformance AS (
    SELECT 
        e.employee_id, e.full_name, d.department_name, dt.year_num,
        AVG(f.performance_rating) AS avg_annual_rating,
        MAX(f.monthly_income) AS annual_salary
    FROM Fact_PerformanceReviews f
    JOIN Dim_Employee e ON f.employee_sk = e.employee_sk
    JOIN Dim_Department d ON f.department_sk = d.department_sk
    JOIN Dim_Date dt ON f.review_date_key = dt.date_key
    WHERE e.employee_id = :emp_id
    GROUP BY e.employee_id, e.full_name, d.department_name, dt.year_num
),
PerformanceTrajectory AS (
    SELECT 
        employee_id, full_name, department_name, year_num, avg_annual_rating, annual_salary,
        LAG(avg_annual_rating, 1) OVER (PARTITION BY employee_id ORDER BY year_num ASC) AS prev_year_rating,
        LAG(annual_salary, 1) OVER (PARTITION BY employee_id ORDER BY year_num ASC) AS prev_year_salary
    FROM AnnualEmployeePerformance
)
SELECT 
    employee_id, full_name, department_name, year_num,
    ROUND(avg_annual_rating, 2) AS rating,
    ROUND(prev_year_rating, 2) AS prev_rating,
    ROUND(avg_annual_rating - prev_year_rating, 2) AS yoy_rating_delta,
    annual_salary, prev_year_salary,
    ROUND(annual_salary - prev_year_salary, 2) AS yoy_salary_increment,
    ROUND(((annual_salary - prev_year_salary) / NULLIF(prev_year_salary, 0)) * 100, 2) AS salary_growth_pct
FROM PerformanceTrajectory
ORDER BY employee_id, year_num ASC;
                """,
                language="sql",
            )

    # -------------------------------------------------------------------------
    # TAB 3: SCD Type 2 Audit Trail using LEAD()
    # -------------------------------------------------------------------------
    with tabs[2]:
        render_section_header("Query 3: SCD Type 2 Career Progression & Audit Trail", "Uses LEAD() to calculate future raise steps between point-in-time dimensional records.")

        emp_list = provider.get_all_employees(limit=20)
        emp_options = {e["employee_id"]: f"{e['full_name']} ({e['job_role']})" for e in emp_list}

        selected_emp_id = st.selectbox(
            "Select Employee to Audit SCD Type 2 History:",
            options=list(emp_options.keys()),
            format_func=lambda x: emp_options.get(x, str(x)),
            key="lead_emp_select",
        )

        selected_name = emp_options.get(selected_emp_id, "Selected Employee").split(" (")[0]
        scd2_df = provider.get_scd2_audit_trail(selected_emp_id)

        if not scd2_df.empty:
            st.plotly_chart(plot_scd2_timeline(scd2_df, selected_name), use_container_width=True)

            scd2_display = scd2_df.copy()
            scd2_display["monthly_income"] = scd2_display["monthly_income"].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "-")
            scd2_display["next_raise_amount"] = scd2_display["next_raise_amount"].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) and x > 0 else ("$0.00" if pd.notnull(x) else "-"))
            scd2_display["is_current"] = scd2_display["is_current"].apply(lambda x: "✅ CURRENT" if x == 1 else "📁 HISTORICAL")

            cols_to_show = ["version", "department_name", "job_role", "job_level", "monthly_income", "next_raise_amount", "effective_start_date", "effective_end_date", "is_current"]
            scd2_display = scd2_display[cols_to_show]
            scd2_display.columns = ["Version", "Department", "Job Role", "Level", "Monthly Income", "Next Raise (LEAD)", "Effective Start", "Effective End", "Status"]
            st.dataframe(scd2_display, use_container_width=True, hide_index=True)
        else:
            st.info(f"No historical SCD Type 2 versions logged for employee #{selected_emp_id}.")

        with st.expander("🔍 View Underlying Advanced SQL Query (LEAD & SCD2)"):
            st.code(
                """
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
WHERE employee_id = :emp_id
ORDER BY employee_id, version ASC;
                """,
                language="sql",
            )

    # -------------------------------------------------------------------------
    # TAB 4: Attrition Risk using NTILE(4)
    # -------------------------------------------------------------------------
    with tabs[3]:
        render_section_header("Query 4: Attrition Risk Analysis & Quartile Segmentation", "Uses NTILE(4) to segment salary bands and correlates sentiment with attrition risks.")

        attr_df = provider.get_attrition_risk_analysis()

        if not attr_df.empty:
            st.plotly_chart(plot_attrition_risk_quartiles(attr_df), use_container_width=True)

            attr_display = attr_df.copy()
            attr_display["salary_quartile"] = attr_display["salary_quartile"].apply(lambda x: f"Q{x} Band")
            attr_display.columns = ["Department", "Calculated Risk Tier", "Salary Quartile (NTILE)", "Headcount", "Avg Rating", "Avg Satisfaction", "Attrited Count"]
            st.dataframe(attr_display, use_container_width=True, hide_index=True)
        else:
            st.info("No attrition risk quartile data available.")

        with st.expander("🔍 View Underlying Advanced SQL Query (CTEs & NTILE 4)"):
            st.code(
                """
WITH EmployeeRiskProfile AS (
    SELECT 
        e.employee_sk, e.full_name, e.department_name, e.job_role, e.attrition,
        f.performance_rating, f.work_life_balance, f.job_satisfaction, f.monthly_income,
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
    department_name, calculated_risk_tier, salary_quartile,
    COUNT(*) AS employee_count,
    ROUND(AVG(performance_rating), 2) AS avg_rating,
    ROUND(AVG(job_satisfaction), 2) AS avg_satisfaction,
    SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END) AS total_attrited
FROM EmployeeRiskProfile
GROUP BY department_name, calculated_risk_tier, salary_quartile
ORDER BY department_name, calculated_risk_tier;
                """,
                language="sql",
            )

    # -------------------------------------------------------------------------
    # TAB 5: Resource Bottlenecks (> 100% Bandwidth)
    # -------------------------------------------------------------------------
    with tabs[4]:
        render_section_header("Query 5: Project Resource Allocation Bottlenecks", "Identifies over-allocated employees committed to > 100% capacity across projects.")

        alloc_df = provider.get_resource_bottlenecks()

        if not alloc_df.empty:
            over_allocated_count = len(alloc_df[alloc_df["total_allocation_pct"] > 100])
            if over_allocated_count > 0:
                st.error(f"🚨 Operational Bottleneck Alert: {over_allocated_count} employee(s) exceed 100% project allocation bandwidth!")
            else:
                st.success("✅ Healthy Capacity: No staff members currently exceed 100% allocation limit.")

            st.plotly_chart(plot_resource_bottlenecks(alloc_df), use_container_width=True)

            alloc_display = alloc_df.copy()
            alloc_display["total_allocation_pct"] = alloc_display["total_allocation_pct"].apply(lambda x: f"{x:.1f}%")
            alloc_display.columns = ["Employee Name", "Department", "Active Assigned Projects", "Total Allocation %", "Bandwidth Status"]
            st.dataframe(alloc_display, use_container_width=True, hide_index=True)
        else:
            st.info("No active project allocation data found.")

        with st.expander("🔍 View Underlying Advanced SQL Query (Allocation Aggregation)"):
            st.code(
                """
WITH TotalStaffAllocation AS (
    SELECT 
        e.employee_sk, e.full_name, e.department_name,
        COUNT(fpa.project_sk) AS assigned_project_count,
        SUM(fpa.allocation_pct) AS total_allocation_pct
    FROM Fact_ProjectAllocations fpa
    JOIN Dim_Employee e ON fpa.employee_sk = e.employee_sk
    WHERE e.is_current = 1
    GROUP BY e.employee_sk, e.full_name, e.department_name
)
SELECT 
    full_name, department_name, assigned_project_count, total_allocation_pct,
    CASE 
        WHEN total_allocation_pct > 100 THEN 'OVER-ALLOCATED (Bottleneck Risk)'
        WHEN total_allocation_pct = 100 THEN 'Fully Utilized'
        ELSE 'Available Bandwidth'
    END AS capacity_status
FROM TotalStaffAllocation
ORDER BY total_allocation_pct DESC;
                """,
                language="sql",
            )

