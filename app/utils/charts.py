"""
Plotly Chart Factory for Executive Dashboards and Analytical Queries.
Generates responsive, interactive corporate visualizations with consistent styling.
"""

from typing import List, Dict, Any
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Enterprise Dark Theme Base Layout
BASE_LAYOUT = dict(
    paper_bgcolor="rgba(15, 23, 42, 0.4)",
    plot_bgcolor="rgba(15, 23, 42, 0.6)",
    font=dict(color="#e2e8f0", family="Segoe UI, sans-serif"),
    margin=dict(l=40, r=40, t=50, b=40),
)

COLOR_PALETTE = ["#38bdf8", "#34d399", "#f59e0b", "#ec4899", "#8b5cf6", "#06b6d4"]


def plot_top_performers(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart of top performing talent ranked by DENSE_RANK()."""
    if df.empty:
        return go.Figure()

    df_sorted = df.sort_values(by=["dept_rank", "monthly_income"], ascending=[False, True])
    fig = px.bar(
        df_sorted,
        x="monthly_income",
        y="full_name",
        color="performance_rating",
        orientation="h",
        color_continuous_scale="Blues",
        labels={"monthly_income": "Monthly Income ($)", "full_name": "Employee", "performance_rating": "Rating (1-5)"},
        hover_data=["department_name", "job_role", "dept_rank", "job_satisfaction"],
        title="Top Performers Ranked by DENSE_RANK() (Rating, Satisfaction & Income)",
    )
    fig.update_layout(**BASE_LAYOUT, height=450)
    fig.update_xaxes(gridcolor="#334155", zerolinecolor="#475569")
    fig.update_yaxes(gridcolor="#334155", zerolinecolor="#475569")
    return fig


def plot_yoy_trajectory(df: pd.DataFrame, employee_name: str = "") -> go.Figure:
    """Dual-axis trajectory chart showing YoY rating and salary increment using LAG()."""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    # Annual Salary Bar
    fig.add_trace(
        go.Bar(
            x=df["year_num"],
            y=df["annual_salary"],
            name="Annual Salary ($)",
            marker_color="#38bdf8",
            opacity=0.75,
            yaxis="y1",
        )
    )

    # Average Performance Rating Line
    fig.add_trace(
        go.Scatter(
            x=df["year_num"],
            y=df["rating"],
            name="Performance Rating",
            mode="lines+markers+text",
            text=df["rating"],
            textposition="top center",
            line=dict(color="#34d399", width=3),
            marker=dict(size=9, color="#10b981"),
            yaxis="y2",
        )
    )

    title = f"YoY Performance & Compensation Trajectory: {employee_name}" if employee_name else "YoY Trajectory"
    fig.update_layout(
        **BASE_LAYOUT,
        title=title,
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(title="Annual Salary ($)", gridcolor="#334155"),
        yaxis2=dict(
            title="Rating (1 to 5)",
            overlaying="y",
            side="right",
            range=[0, 5.5],
            showgrid=False,
            color="#34d399",
        ),
        xaxis=dict(title="Evaluation Year", tickmode="linear", gridcolor="#334155"),
    )
    return fig


def plot_scd2_timeline(df: pd.DataFrame, employee_name: str = "") -> go.Figure:
    """Visualizes SCD Type 2 Historical Career Progression Versions using LEAD()."""
    if df.empty:
        return go.Figure()

    df_sorted = df.sort_values(by="version", ascending=True)

    fig = go.Figure()

    # Step line of salary progression across versions
    fig.add_trace(
        go.Scatter(
            x=df_sorted["version"].astype(str),
            y=df_sorted["monthly_income"],
            mode="lines+markers+text",
            line=dict(shape="hv", color="#f59e0b", width=3),
            marker=dict(size=12, symbol="diamond", color="#fbbf24"),
            text=[f"${x:,.0f} ({r})" for x, r in zip(df_sorted["monthly_income"], df_sorted["job_role"])],
            textposition="top left",
            name="Monthly Income ($)",
        )
    )

    title = f"SCD Type 2 Career Progression Audit Trail: {employee_name}" if employee_name else "SCD Type 2 Timeline"
    fig.update_layout(
        **BASE_LAYOUT,
        title=title,
        height=400,
        xaxis=dict(title="SCD Type 2 Version #", type="category", gridcolor="#334155"),
        yaxis=dict(title="Monthly Income ($)", gridcolor="#334155"),
    )
    return fig


def plot_attrition_risk_quartiles(df: pd.DataFrame) -> go.Figure:
    """Grouped bar chart displaying risk tiers categorized across salary quartiles (NTILE 4)."""
    if df.empty:
        return go.Figure()

    color_map = {
        "High Attrition Risk": "#f87171",
        "Moderate Risk": "#fbbf24",
        "Low Risk": "#34d399",
    }

    fig = px.bar(
        df,
        x="salary_quartile",
        y="employee_count",
        color="calculated_risk_tier",
        barmode="group",
        color_discrete_map=color_map,
        labels={"salary_quartile": "Salary Quartile (1=Lowest, 4=Highest)", "employee_count": "Employee Count", "calculated_risk_tier": "Risk Tier"},
        title="Attrition Sentiment Risk Breakdown Across Salary Quartiles (NTILE 4)",
        hover_data=["department_name", "avg_satisfaction", "total_attrited"],
    )
    fig.update_layout(**BASE_LAYOUT, height=420)
    fig.update_xaxes(gridcolor="#334155")
    fig.update_yaxes(gridcolor="#334155")
    return fig


def plot_resource_bottlenecks(df: pd.DataFrame) -> go.Figure:
    """Bar chart highlighting over-allocated employees vs available capacity."""
    if df.empty:
        return go.Figure()

    df_top = df.head(15).copy()

    # Color threshold: > 100% is Red/Risk
    colors = [
        "#f87171" if val > 100 else ("#fbbf24" if val == 100 else "#38bdf8")
        for val in df_top["total_allocation_pct"]
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df_top["full_name"],
            y=df_top["total_allocation_pct"],
            marker_color=colors,
            text=[f"{v:.0f}%" for v in df_top["total_allocation_pct"]],
            textposition="outside",
            name="Committed Allocation %",
        )
    )

    # Threshold line at 100% capacity
    fig.add_hline(
        y=100,
        line_dash="dot",
        line_color="#ef4444",
        annotation_text="100% Max Capacity Limit",
        annotation_position="bottom right",
    )

    fig.update_layout(
        **BASE_LAYOUT,
        title="Project Allocation Bandwidth & Bottleneck Detector (>100% Risk)",
        height=420,
        xaxis=dict(title="Employee", tickangle=-45, gridcolor="#334155"),
        yaxis=dict(title="Total Allocation %", range=[0, max(120, df_top["total_allocation_pct"].max() + 15)], gridcolor="#334155"),
    )
    return fig


def plot_department_headcount(df: pd.DataFrame) -> go.Figure:
    """Donut chart showing headcount distribution across departments."""
    if df.empty:
        return go.Figure()

    fig = px.pie(
        df,
        names="department_name",
        values="headcount",
        hole=0.45,
        color_discrete_sequence=COLOR_PALETTE,
        title="Department Headcount Distribution",
    )
    fig.update_layout(**BASE_LAYOUT, height=380)
    return fig


def plot_department_salary_distribution(df: pd.DataFrame) -> go.Figure:
    """Bar chart of average monthly compensation per department."""
    if df.empty:
        return go.Figure()

    fig = px.bar(
        df,
        x="department_name",
        y="avg_salary",
        color="avg_salary",
        color_continuous_scale="Viridis",
        labels={"department_name": "Department", "avg_salary": "Avg Monthly Compensation ($)"},
        title="Average Monthly Compensation by Department",
        text_auto=".2s",
    )
    fig.update_layout(**BASE_LAYOUT, height=380)
    fig.update_xaxes(gridcolor="#334155")
    fig.update_yaxes(gridcolor="#334155")
    return fig
