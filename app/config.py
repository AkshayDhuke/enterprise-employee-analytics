"""
Application Configuration and Constants.
Provides environment-aware settings and branding definitions for Streamlit UI.
"""

import os
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
SQL_DIR = ROOT_DIR / "sql"

# Application Metadata
APP_TITLE = "Enterprise HR Analytics & Warehouse System"
APP_SUBTITLE = "OLTP Operations, Dimensional Warehouse & Executive Analytics"
APP_ICON = "🏢"

# Navigation Menu Options
PAGES = {
    "kpi_overview": "Executive KPI Overview",
    "advanced_analytics": "Advanced SQL & Window Functions",
    "employee_ops": "Employee Directory & SCD Type 2",
    "project_allocations": "Project Allocations & Capacity",
    "review_hub": "Performance Review Evaluation",
    "warehouse_admin": "Data Warehouse & DB Health",
}

# Departments list
DEFAULT_DEPARTMENTS = [
    {"department_id": 1, "department_name": "Research & Development", "cost_center_code": "CC-101", "location": "Building A - HQ"},
    {"department_id": 2, "department_name": "Sales", "cost_center_code": "CC-202", "location": "Building B - East"},
    {"department_id": 3, "department_name": "Human Resources", "cost_center_code": "CC-303", "location": "Building A - HQ"},
    {"department_id": 4, "department_name": "Engineering & IT", "cost_center_code": "CC-404", "location": "Innovation Hub"},
    {"department_id": 5, "department_name": "Finance & Operations", "cost_center_code": "CC-505", "location": "Building C - South"},
]

# Standard Job Roles
JOB_ROLES = [
    "Software Engineer",
    "Senior Software Engineer",
    "Lead Architect",
    "Research Scientist",
    "Laboratory Technician",
    "Sales Executive",
    "Sales Representative",
    "Manager",
    "Healthcare Representative",
    "Human Resources Specialist",
]

# Education Fields
EDUCATION_FIELDS = [
    "Life Sciences",
    "Medical",
    "Marketing",
    "Technical Degree",
    "Computer Science",
    "Other",
]

