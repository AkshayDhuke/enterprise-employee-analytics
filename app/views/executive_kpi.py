"""
Executive KPI Overview View.
Displays corporate-level workforce metrics, department distributions, and executive summaries.
"""

import streamlit as st
import pandas as pd
from app.data_provider import DataProvider
from app.utils.ui_helpers import render_metric_card, render_section_header
from app.utils.charts import plot_department_headcount, plot_department_salary_distribution


def render_executive_kpi_view(provider: DataProvider):
    """Renders the executive summary dashboard."""
    st.title("📊 Executive Workforce & Operational Overview")
    st.markdown("High-level executive metrics aggregating corporate headcount, retention, and compensation.")

    # Fetch KPIs
    kpis = provider.get_executive_kpis()
    dept_df = provider.get_department_summary()

    # Global Department Filter
    dept_options = ["All Departments"] + list(dept_df["department_name"].unique()) if not dept_df.empty else ["All Departments"]
    selected_dept = st.selectbox("🎯 Filter Executive Scope by Department:", dept_options)

    # Filter metrics if department selected
    if selected_dept != "All Departments" and not dept_df.empty:
        filtered_dept = dept_df[dept_df["department_name"] == selected_dept].iloc[0]
        headcount = int(filtered_dept["headcount"])
        avg_income = float(filtered_dept["avg_salary"])
        attrited = int(filtered_dept["attrited"])
        attrition_rate = round((attrited / headcount) * 100, 2) if headcount else 0.0
    else:
        headcount = kpis.get("total_headcount", 0)
        avg_income = kpis.get("avg_monthly_income", 0.0)
        attrition_rate = kpis.get("attrition_rate", 0.0)

    # -------------------------------------------------------------------------
    # Top Row: 6 Executive KPI Metric Cards
    # -------------------------------------------------------------------------
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        render_metric_card(
            title="Total Headcount",
            value=f"{headcount:,}",
            delta="+4.2% YoY" if selected_dept == "All Departments" else "Dept Staff",
            delta_type="positive",
            icon="👥"
        )
    with c2:
        render_metric_card(
            title="Avg Monthly Pay",
            value=f"${avg_income:,.0f}",
            delta="+5.8% Annual Growth",
            delta_type="positive",
            icon="💵"
        )
    with c3:
        render_metric_card(
            title="Attrition Rate",
            value=f"{attrition_rate:.1f}%",
            delta="-1.8% vs Benchmark",
            delta_type="positive" if attrition_rate < 15 else "negative",
            icon="📉"
        )
    with c4:
        render_metric_card(
            title="Avg Rating",
            value=f"{kpis.get('avg_performance_rating', 0.0):.2f} / 5",
            delta="Rating Standard",
            delta_type="neutral",
            icon="⭐"
        )
    with c5:
        render_metric_card(
            title="Job Satisfaction",
            value=f"{kpis.get('avg_job_satisfaction', 0.0):.2f} / 5",
            delta="Sentiment Index",
            delta_type="positive",
            icon="😊"
        )
    with c6:
        render_metric_card(
            title="Active Projects",
            value=f"{kpis.get('active_projects', 0)} / {kpis.get('total_projects', 0)}",
            delta=f"${kpis.get('total_budget', 0):,.0f} Budget",
            delta_type="neutral",
            icon="📁"
        )

    st.divider()

    # -------------------------------------------------------------------------
    # Middle Section: Charts
    # -------------------------------------------------------------------------
    render_section_header("Corporate Distribution Breakdown", "Staffing allocation and compensation parity across business units.")
    
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.plotly_chart(plot_department_headcount(dept_df), use_container_width=True)
    with col_chart2:
        st.plotly_chart(plot_department_salary_distribution(dept_df), use_container_width=True)

    # -------------------------------------------------------------------------
    # Bottom Section: Department Summary Data Table
    # -------------------------------------------------------------------------
    render_section_header("Department Performance & Compensation Summary")
    if not dept_df.empty:
        display_df = dept_df.copy()
        display_df["avg_salary"] = display_df["avg_salary"].apply(lambda x: f"${x:,.2f}")
        display_df.columns = ["Department Name", "Active Headcount", "Average Monthly Salary", "Total Attrition"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

