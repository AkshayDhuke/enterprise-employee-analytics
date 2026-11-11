"""
Phase 4: Analytics Dashboard (OLAP Interaction)
Simple, clean executive dashboard connected to the Star Schema Data Warehouse.
Visualizes:
1. High-Level Executive KPIs
2. Top-Performing Employees by Department (using SQL Window Function DENSE_RANK)
3. Year-over-Year Performance & Salary Trends (using SQL Window Function LAG)
4. Employee Attrition Risk & Bottlenecks (using SQL Window Function NTILE 4)
"""

import streamlit as st
import pandas as pd
from app.data_provider import DataProvider
from app.utils.charts import (
    plot_top_performers,
    plot_yoy_trajectory,
    plot_attrition_risk_quartiles,
    plot_resource_bottlenecks,
)


def render_analytics_dashboard(provider: DataProvider):
    st.title("📊 Executive Analytics Dashboard")
    st.caption("OLAP Star Schema Analytics powered by SQL Window Functions (DENSE_RANK, LAG, NTILE)")

    # -------------------------------------------------------------------------
    # 1. High-Level Executive KPIs
    # -------------------------------------------------------------------------
    kpis = provider.get_executive_kpis()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Workforce",
            value=f"{kpis.get('total_headcount', 0):,}",
            help="Total active and historical workforce records in the warehouse.",
        )
    with col2:
        attr_rate = kpis.get("attrition_rate", 0.0)
        st.metric(
            label="Attrition Rate",
            value=f"{attr_rate:.1f}%",
            delta=f"-{attr_rate:.1f}%" if attr_rate > 15 else "Normal",
            delta_color="inverse",
            help="Percentage of employees who have left the organization.",
        )
    with col3:
        avg_inc = kpis.get("avg_monthly_income", 0.0)
        st.metric(
            label="Avg Monthly Income",
            value=f"${avg_inc:,.2f}",
            help="Average monthly base compensation across all job tiers.",
        )
    with col4:
        avg_perf = kpis.get("avg_performance_rating", 0.0)
        st.metric(
            label="Avg Performance Rating",
            value=f"{avg_perf:.2f} / 5.0",
            help="Average overall performance rating from annual reviews.",
        )

    st.divider()

    # -------------------------------------------------------------------------
    # 2. Analytics Tabs (Directly asked in project requirements)
    # -------------------------------------------------------------------------
    tab1, tab2, tab3 = st.tabs([
        "🏆 Top Performers (DENSE_RANK)",
        "📈 YoY Performance & Salary (LAG)",
        "⚠️ Attrition Risk & Bottlenecks (NTILE)",
    ])

    # -------------------------------------------------------------------------
    # TAB 1: Top Performers (DENSE_RANK)
    # -------------------------------------------------------------------------
    with tab1:
        st.subheader("Top-Performing Employees by Department")
        st.info("💡 **SQL Concept:** Uses `DENSE_RANK() OVER (PARTITION BY department_name ORDER BY performance_rating DESC)` on the Star Schema to rank top talent without gaps.")

        c1, c2 = st.columns([2, 1])
        with c1:
            depts = ["All", "Sales", "Research & Development", "Human Resources", "Engineering & IT", "Finance & Operations"]
            selected_dept = st.selectbox("Select Department:", depts, key="dash_dense_dept")
        with c2:
            top_n = st.slider("Top N Ranks:", min_value=1, max_value=10, value=5, key="dash_dense_n")

        dept_arg = None if selected_dept == "All" else selected_dept
        df_rank = provider.get_top_performers(department_name=dept_arg, top_n=top_n)

        if not df_rank.empty:
            st.plotly_chart(plot_top_performers(df_rank), use_container_width=True)

            table_df = df_rank.copy()
            if "monthly_income" in table_df.columns:
                table_df["monthly_income"] = table_df["monthly_income"].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "-")
            table_df.columns = [c.replace("_", " ").title() for c in table_df.columns]
            st.dataframe(table_df, use_container_width=True, hide_index=True)
        else:
            st.warning("No records found for the selected department.")

    # -------------------------------------------------------------------------
    # TAB 2: YoY Performance & Salary Trends (LAG)
    # -------------------------------------------------------------------------
    with tab2:
        st.subheader("Year-over-Year Performance & Compensation Trajectory")
        st.info("💡 **SQL Concept:** Uses `LAG(performance_rating, 1)` and `LAG(monthly_income, 1)` to calculate year-over-year rating deltas and salary bumps across consecutive review cycles.")

        # Employee selector for trajectory
        all_emps = provider.get_all_employees(limit=25)
        emp_options = {e["employee_id"]: f"{e['full_name']} ({e['job_role']} - {e['department_name']})" for e in all_emps}
        
        default_id = list(emp_options.keys())[0] if emp_options else 101
        selected_emp_id = st.selectbox(
            "Select Employee to Analyze:",
            options=list(emp_options.keys()),
            format_func=lambda x: emp_options.get(x, f"Employee #{x}"),
            index=0,
            key="dash_yoy_emp",
        )

        df_yoy = provider.get_yoy_trajectory(employee_id=selected_emp_id)

        if not df_yoy.empty:
            st.plotly_chart(plot_yoy_trajectory(df_yoy), use_container_width=True)

            disp_yoy = df_yoy.copy()
            if "annual_salary" in disp_yoy.columns:
                disp_yoy["annual_salary"] = disp_yoy["annual_salary"].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "-")
            if "yoy_salary_increment" in disp_yoy.columns:
                disp_yoy["yoy_salary_increment"] = disp_yoy["yoy_salary_increment"].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "-")
            disp_yoy.columns = [c.replace("_", " ").title() for c in disp_yoy.columns]
            st.dataframe(disp_yoy, use_container_width=True, hide_index=True)
        else:
            st.info("No historical review data available for this employee.")

    # -------------------------------------------------------------------------
    # TAB 3: Attrition Risk & Bottlenecks (NTILE 4)
    # -------------------------------------------------------------------------
    with tab3:
        st.subheader("Employee Attrition Risk & Resource Bottleneck Analysis")
        st.info("💡 **SQL Concept:** Uses `NTILE(4) OVER (ORDER BY monthly_income)` to segment the workforce into income quartiles, correlating compensation vs. overtime workload to pinpoint burnout.")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("#### Salary Quartile Flight Risk")
            df_risk = provider.get_attrition_risk_analysis()
            if not df_risk.empty:
                st.plotly_chart(plot_attrition_risk_quartiles(df_risk), use_container_width=True)
                st.caption("Quartile 1 (Lowest 25% compensation) demonstrates highest attrition probability.")

        with col_b:
            st.markdown("#### Project Staffing & Bottleneck Analysis")
            df_bottlenecks = provider.get_resource_bottlenecks()
            if not df_bottlenecks.empty:
                st.plotly_chart(plot_resource_bottlenecks(df_bottlenecks), use_container_width=True)
                st.caption("Identifies employees over-allocated (>100% capacity across projects).")
