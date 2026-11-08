"""
Phase 4 Verification & Unit Test Suite
Validates Streamlit DataProvider, Analytical query pipelines, Plotly chart generation,
and OLTP/DW operational synchronization.
"""

import unittest
from datetime import date
import pandas as pd

from app.data_provider import DataProvider
from app.utils.charts import (
    plot_top_performers,
    plot_yoy_trajectory,
    plot_scd2_timeline,
    plot_attrition_risk_quartiles,
    plot_resource_bottlenecks,
    plot_department_headcount,
    plot_department_salary_distribution,
)


class TestPhase4DataProvider(unittest.TestCase):
    """Verifies DataProvider methods, fallbacks, and data transformations."""

    def setUp(self):
        self.provider = DataProvider()

    def test_executive_kpis(self):
        """Verifies KPI extraction format and non-empty values."""
        kpis = self.provider.get_executive_kpis()
        self.assertIn("total_headcount", kpis)
        self.assertIn("avg_monthly_income", kpis)
        self.assertIn("attrition_rate", kpis)
        self.assertIn("avg_performance_rating", kpis)
        self.assertGreater(kpis["total_headcount"], 0)

    def test_query1_top_performers_dense_rank(self):
        """Verifies Query 1 DENSE_RANK partitioning and column structure."""
        df = self.provider.get_top_performers(top_n=3)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        required_cols = ["dept_rank", "year_num", "department_name", "full_name", "performance_rating", "monthly_income"]
        for col in required_cols:
            self.assertIn(col, df.columns)
        self.assertTrue((df["dept_rank"] <= 3).all())

    def test_query2_yoy_trajectory_lag(self):
        """Verifies Query 2 LAG trajectory calculation and delta columns."""
        df = self.provider.get_yoy_trajectory(employee_id=101)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        required_cols = ["year_num", "rating", "prev_rating", "yoy_rating_delta", "annual_salary", "yoy_salary_increment"]
        for col in required_cols:
            self.assertIn(col, df.columns)

    def test_query3_scd2_audit_trail_lead(self):
        """Verifies Query 3 LEAD salary increment and SCD Type 2 versions."""
        df = self.provider.get_scd2_audit_trail(employee_id=101)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        self.assertIn("version", df.columns)
        self.assertIn("effective_start_date", df.columns)
        self.assertIn("effective_end_date", df.columns)
        self.assertIn("is_current", df.columns)

    def test_query4_attrition_risk_ntile(self):
        """Verifies Query 4 NTILE salary quartile segmentation and risk tiers."""
        df = self.provider.get_attrition_risk_analysis()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        self.assertIn("salary_quartile", df.columns)
        self.assertIn("calculated_risk_tier", df.columns)
        self.assertIn("employee_count", df.columns)

    def test_query5_resource_bottlenecks(self):
        """Verifies Query 5 resource allocation bottleneck identification."""
        df = self.provider.get_resource_bottlenecks()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        self.assertIn("total_allocation_pct", df.columns)
        self.assertIn("capacity_status", df.columns)

    def test_employee_creation_and_scd2_progression(self):
        """Verifies adding employee and triggering SCD Type 2 career promotion."""
        new_emp = {
            "first_name": "Test",
            "last_name": "User",
            "email": "test.user@enterprise.com",
            "department_id": 4,
            "job_role": "Software Engineer",
            "job_level": 2,
            "monthly_income": 7000.0,
            "hire_date": str(date.today()),
        }
        emp_id = self.provider.create_employee(new_emp)
        self.assertIsNotNone(emp_id)

        # Trigger SCD2 Promotion
        promoted = self.provider.update_employee_scd2(
            employee_id=emp_id,
            new_dept_id=4,
            new_role="Senior Software Engineer",
            new_level=3,
            new_salary=8500.0,
            effective_date=date.today(),
        )
        self.assertTrue(promoted)

    def test_project_and_review_submissions(self):
        """Verifies project registration and review submission pipelines."""
        proj_id = self.provider.create_project({
            "project_name": "Cloud Native AI Pipeline",
            "department_id": 1,
            "priority": "High",
            "status": "Active",
            "budget": 500000.0,
        })
        self.assertIsNotNone(proj_id)

        rev_id = self.provider.submit_review({
            "employee_id": 101,
            "review_date": str(date.today()),
            "review_cycle": "Annual Review",
            "performance_rating": 4.8,
            "job_satisfaction": 4,
            "work_life_balance": 3,
            "training_times_last_year": 4,
            "reviewer_comments": "Exceeded all engineering delivery goals.",
        })
        self.assertIsNotNone(rev_id)


class TestPhase4ChartFactory(unittest.TestCase):
    """Verifies Plotly chart rendering without exceptions."""

    def setUp(self):
        self.provider = DataProvider()

    def test_all_chart_renderers(self):
        """Ensures all chart generation functions return valid Plotly Figures."""
        top_df = self.provider.get_top_performers()
        fig_top = plot_top_performers(top_df)
        self.assertIsNotNone(fig_top)

        yoy_df = self.provider.get_yoy_trajectory(101)
        fig_yoy = plot_yoy_trajectory(yoy_df, "Sarah Chen")
        self.assertIsNotNone(fig_yoy)

        scd2_df = self.provider.get_scd2_audit_trail(101)
        fig_scd2 = plot_scd2_timeline(scd2_df, "Sarah Chen")
        self.assertIsNotNone(fig_scd2)

        attr_df = self.provider.get_attrition_risk_analysis()
        fig_attr = plot_attrition_risk_quartiles(attr_df)
        self.assertIsNotNone(fig_attr)

        alloc_df = self.provider.get_resource_bottlenecks()
        fig_alloc = plot_resource_bottlenecks(alloc_df)
        self.assertIsNotNone(fig_alloc)

        dept_df = self.provider.get_department_summary()
        fig_headcount = plot_department_headcount(dept_df)
        self.assertIsNotNone(fig_headcount)

        fig_sal = plot_department_salary_distribution(dept_df)
        self.assertIsNotNone(fig_sal)


if __name__ == "__main__":
    unittest.main()

