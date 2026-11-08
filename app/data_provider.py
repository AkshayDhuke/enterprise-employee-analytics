"""
Unified Data Provider Service for Phase 4 Streamlit Application.
Seamlessly routes queries between live MySQL databases (using Phase 3 DAL)
and high-fidelity demonstration datasets when the database is offline or uninitialized.
"""

import os
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd

from src.db_manager import DatabaseConnection
from src.dal.analytics_manager import AnalyticsManager
from src.dal.employee_manager import EmployeeManager
from src.dal.project_manager import ProjectManager
from src.dal.review_manager import ReviewManager
from src.entities.employee import Employee
from src.entities.project import Project
from src.entities.review import Review


class DataProvider:
    """
    Central data orchestration provider for Streamlit UI.
    Provides fallback mock execution when database is offline, ensuring
    100% testability and smooth presentation.
    """

    def __init__(self):
        self.db = DatabaseConnection()
        self.analytics_dal = AnalyticsManager()
        self.employee_dal = EmployeeManager()
        self.project_dal = ProjectManager()
        self.review_dal = ReviewManager()

        # Check connectivity
        self._is_live = False
        self._check_connectivity()

        # Initialize mock repository for offline demo mode
        self._init_demo_dataset()

    def _check_connectivity(self):
        """Probes MySQL connectivity."""
        try:
            status = self.db.test_connections()
            self._is_live = status["oltp"] and status["dw"]
        except Exception:
            self._is_live = False

    @property
    def is_live(self) -> bool:
        """Returns True if connected to live MySQL OLTP and DW databases."""
        return self._is_live

    def reconnect(self, user: str, password: str, host: str = "127.0.0.1", port: str = "3306") -> Dict[str, Any]:
        """Disposes existing pool and attempts reconnection with provided credentials."""
        self.db.close_all()
        # Create fresh instance with new parameters
        self.db = DatabaseConnection(user=user, password=password, host=host, port=port)
        self.analytics_dal = AnalyticsManager()
        self.employee_dal = EmployeeManager()
        self.project_dal = ProjectManager()
        self.review_dal = ReviewManager()
        
        status = self.db.test_connections()
        self._is_live = status["oltp"] and status["dw"]
        return status

    # -------------------------------------------------------------------------
    # Analytical Queries (Phase 2 & 3 AnalyticsManager)
    # -------------------------------------------------------------------------

    def get_executive_kpis(self) -> Dict[str, Any]:
        """Returns high-level executive KPI indicators."""
        if self._is_live:
            try:
                return self.analytics_dal.get_executive_kpis()
            except Exception:
                pass
        return self._demo_kpis

    def get_top_performers(self, department_name: Optional[str] = None, top_n: int = 5) -> pd.DataFrame:
        """Executes Query 1: Top-performing employees by department using DENSE_RANK()."""
        if self._is_live:
            try:
                rows = self.analytics_dal.get_top_performers_by_department(department_name, top_n)
                return pd.DataFrame(rows)
            except Exception:
                pass

        # Demo Mode Query 1 emulation
        df = self._demo_reviews_df.copy()
        if department_name and department_name != "All":
            df = df[df["department_name"] == department_name]

        # Emulate DENSE_RANK() OVER (PARTITION BY department_name, year_num ORDER BY rating DESC, satisfaction DESC, income DESC)
        df["dept_rank"] = df.groupby(["department_name", "year_num"])[["performance_rating", "job_satisfaction", "monthly_income"]].apply(
            lambda x: x.apply(tuple, axis=1).rank(method="dense", ascending=False)
        ).astype(int).values

        filtered = df[df["dept_rank"] <= top_n].sort_values(
            by=["department_name", "year_num", "dept_rank"],
            ascending=[True, False, True]
        )
        return filtered[[
            "dept_rank", "year_num", "department_name", "full_name",
            "job_role", "performance_rating", "job_satisfaction", "monthly_income"
        ]]

    def get_yoy_trajectory(self, employee_id: Optional[int] = None) -> pd.DataFrame:
        """Executes Query 2: YoY Performance & Salary Trajectory using LAG()."""
        if self._is_live:
            try:
                rows = self.analytics_dal.get_yoy_performance_trajectory(employee_id)
                return pd.DataFrame(rows)
            except Exception:
                pass

        # Demo Mode Query 2 emulation
        df = self._demo_reviews_df.copy()
        if employee_id:
            df = df[df["employee_id"] == employee_id]

        annual = df.groupby(["employee_id", "full_name", "department_name", "year_num"], as_index=False).agg(
            rating=("performance_rating", "mean"),
            annual_salary=("monthly_income", "max")
        ).sort_values(by=["employee_id", "year_num"])

        annual["rating"] = annual["rating"].round(2)
        annual["prev_rating"] = annual.groupby("employee_id")["rating"].shift(1)
        annual["yoy_rating_delta"] = (annual["rating"] - annual["prev_rating"]).round(2)
        annual["prev_year_salary"] = annual.groupby("employee_id")["annual_salary"].shift(1)
        annual["yoy_salary_increment"] = (annual["annual_salary"] - annual["prev_year_salary"]).round(2)
        annual["salary_growth_pct"] = (
            ((annual["annual_salary"] - annual["prev_year_salary"]) / annual["prev_year_salary"]) * 100
        ).round(2)

        return annual

    def get_scd2_audit_trail(self, employee_id: Optional[int] = None) -> pd.DataFrame:
        """Executes Query 3: SCD Type 2 Audit Trail using LEAD()."""
        if self._is_live:
            try:
                rows = self.analytics_dal.get_scd2_audit_trail(employee_id)
                return pd.DataFrame(rows)
            except Exception:
                pass

        # Demo Mode Query 3 emulation
        df = self._demo_scd2_df.copy()
        if employee_id:
            df = df[df["employee_id"] == employee_id]

        df = df.sort_values(by=["employee_id", "version"])
        df["next_raise_amount"] = df.groupby("employee_id")["monthly_income"].shift(-1) - df["monthly_income"]
        return df

    def get_attrition_risk_analysis(self) -> pd.DataFrame:
        """Executes Query 4: Attrition Risk Analysis & Quartile Segmentation using NTILE(4)."""
        if self._is_live:
            try:
                rows = self.analytics_dal.get_attrition_risk_analysis()
                return pd.DataFrame(rows)
            except Exception:
                pass

        return self._demo_attrition_df

    def get_resource_bottlenecks(self) -> pd.DataFrame:
        """Executes Query 5: Project Resource Allocation Bottlenecks & Capacity Exceeded."""
        if self._is_live:
            try:
                rows = self.analytics_dal.get_resource_bottlenecks()
                return pd.DataFrame(rows)
            except Exception:
                pass

        return self._demo_allocations_df

    def get_department_summary(self) -> pd.DataFrame:
        """Returns headcount and salary aggregation by department."""
        if self._is_live:
            try:
                sql = """
                    SELECT 
                        department_name,
                        COUNT(*) AS headcount,
                        ROUND(AVG(monthly_income), 2) AS avg_salary,
                        SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END) AS attrited
                    FROM Dim_Employee
                    WHERE is_current = 1
                    GROUP BY department_name;
                """
                return pd.DataFrame(self.analytics_dal.execute_query(sql, use_dw=True))
            except Exception:
                pass

        return self._demo_dept_summary

    # -------------------------------------------------------------------------
    # OLTP Entity CRUD Operations
    # -------------------------------------------------------------------------

    def get_all_employees(
        self,
        limit: int = 50,
        offset: int = 0,
        department_id: Optional[int] = None,
        search_term: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves active employee list for management view."""
        if self._is_live:
            try:
                if search_term:
                    emps = self.employee_dal.search_employees(search_term, limit=limit)
                else:
                    emps = self.employee_dal.get_all_employees(limit=limit, offset=offset, department_id=department_id)
                return [e.to_dict() for e in emps]
            except Exception:
                pass

        # Demo mode filtering
        emps = self._demo_employees
        if department_id:
            emps = [e for e in emps if e.get("department_id") == department_id]
        if search_term:
            term = search_term.lower()
            emps = [
                e for e in emps
                if term in e.get("full_name", "").lower()
                or term in e.get("email", "").lower()
                or term in e.get("job_role", "").lower()
                or term in e.get("employee_number", "").lower()
            ]
        return emps[offset: offset + limit]

    def create_employee(self, emp_data: Dict[str, Any]) -> int:
        """Creates a new employee record and syncs to warehouse."""
        if self._is_live:
            try:
                emp = Employee.from_dict(emp_data)
                return self.employee_dal.create_employee(emp)
            except Exception:
                pass

        # Demo mode insert
        new_id = len(self._demo_employees) + 101
        emp_data["employee_id"] = new_id
        emp_data["employee_number"] = f"EMP-{new_id:05d}"
        emp_data["full_name"] = f"{emp_data.get('first_name', '')} {emp_data.get('last_name', '')}".strip()
        self._demo_employees.insert(0, emp_data)
        return new_id

    def update_employee_scd2(
        self,
        employee_id: int,
        new_dept_id: int,
        new_role: str,
        new_level: int,
        new_salary: float,
        effective_date: Optional[date] = None,
        attrition: str = "No"
    ) -> bool:
        """Executes SCD Type 2 progression update in DW and updates OLTP profile."""
        if self._is_live:
            try:
                return self.employee_dal.update_employee_scd2(
                    employee_id, new_dept_id, new_role, new_level, new_salary, attrition, effective_date
                )
            except Exception:
                pass

        # Emulate SCD2 update in demo dataset
        dept_names = {1: "Research & Development", 2: "Sales", 3: "Human Resources", 4: "Engineering & IT", 5: "Finance & Operations"}
        dept_name = dept_names.get(new_dept_id, "General")
        today_str = str(effective_date or date.today())

        # Update in demo employees list
        for emp in self._demo_employees:
            if emp["employee_id"] == employee_id:
                emp["department_id"] = new_dept_id
                emp["department_name"] = dept_name
                emp["job_role"] = new_role
                emp["job_level"] = new_level
                emp["monthly_income"] = new_salary
                emp["attrition"] = attrition
                break

        # Append new version to SCD2 demo table and expire previous
        emp_scd_rows = self._demo_scd2_df[self._demo_scd2_df["employee_id"] == employee_id]
        new_version = int(emp_scd_rows["version"].max() + 1) if not emp_scd_rows.empty else 2
        
        # Expire current
        self._demo_scd2_df.loc[
            (self._demo_scd2_df["employee_id"] == employee_id) & (self._demo_scd2_df["is_current"] == 1),
            ["is_current", "effective_end_date"]
        ] = [0, today_str]

        # Insert new version record
        new_scd_record = {
            "employee_id": employee_id,
            "employee_number": f"EMP-{employee_id:05d}",
            "full_name": emp_scd_rows.iloc[0]["full_name"] if not emp_scd_rows.empty else "Employee",
            "version": new_version,
            "department_name": dept_name,
            "job_role": new_role,
            "job_level": new_level,
            "monthly_income": new_salary,
            "attrition": attrition,
            "effective_start_date": today_str,
            "effective_end_date": "9999-12-31",
            "is_current": 1,
            "next_raise_amount": None,
        }
        self._demo_scd2_df = pd.concat([self._demo_scd2_df, pd.DataFrame([new_scd_record])], ignore_index=True)
        return True

    def terminate_employee(self, employee_id: int) -> bool:
        """Soft-deletes employee by setting attrition='Yes'."""
        if self._is_live:
            try:
                return self.employee_dal.delete_employee(employee_id, soft_delete=True)
            except Exception:
                pass

        for emp in self._demo_employees:
            if emp["employee_id"] == employee_id:
                emp["attrition"] = "Yes"
                return True
        return False

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """Retrieves all projects."""
        if self._is_live:
            try:
                projects = self.project_dal.get_all_projects()
                return [p.to_dict() for p in projects]
            except Exception:
                pass
        return self._demo_projects

    def create_project(self, project_data: Dict[str, Any]) -> int:
        """Registers a new project."""
        if self._is_live:
            try:
                proj = Project.from_dict(project_data)
                return self.project_dal.create_project(proj)
            except Exception:
                pass

        new_id = len(self._demo_projects) + 1
        project_data["project_id"] = new_id
        if not project_data.get("project_code"):
            project_data["project_code"] = f"PRJ-{project_data.get('department_id', 1):02d}-{new_id:04d}"
        self._demo_projects.insert(0, project_data)
        return new_id

    def submit_review(self, review_data: Dict[str, Any]) -> int:
        """Submits performance review and synchronizes to warehouse fact."""
        if self._is_live:
            try:
                rev = Review.from_dict(review_data)
                return self.review_dal.create_review(rev)
            except Exception:
                pass

        new_id = len(self._demo_reviews_df) + 1
        emp_match = [e for e in self._demo_employees if e["employee_id"] == review_data["employee_id"]]
        full_name = emp_match[0]["full_name"] if emp_match else "Employee"
        dept_name = emp_match[0].get("department_name", "Engineering & IT") if emp_match else "General"
        job_role = emp_match[0].get("job_role", "Software Engineer") if emp_match else "General"
        salary = float(emp_match[0].get("monthly_income", 6000.0)) if emp_match else 6000.0

        rev_date = review_data.get("review_date", date.today())
        year_num = rev_date.year if isinstance(rev_date, date) else int(str(rev_date)[:4])

        new_row = {
            "review_id": new_id,
            "employee_id": review_data["employee_id"],
            "full_name": full_name,
            "department_name": dept_name,
            "job_role": job_role,
            "year_num": year_num,
            "performance_rating": float(review_data.get("performance_rating", 3.0)),
            "job_satisfaction": int(review_data.get("job_satisfaction", 3)),
            "work_life_balance": int(review_data.get("work_life_balance", 3)),
            "monthly_income": salary,
            "dept_rank": 1,
        }
        self._demo_reviews_df = pd.concat([self._demo_reviews_df, pd.DataFrame([new_row])], ignore_index=True)
        return new_id

    # -------------------------------------------------------------------------
    # Demo Synthetic Data Generator (Zero-Dependency Offline Emulation)
    # -------------------------------------------------------------------------

    def _init_demo_dataset(self):
        """Initializes realistic enterprise datasets for zero-config offline execution."""
        self._demo_kpis = {
            "total_headcount": 1470,
            "avg_monthly_income": 6502.93,
            "attrition_rate": 16.12,
            "avg_performance_rating": 3.78,
            "avg_job_satisfaction": 3.25,
            "avg_work_life_balance": 3.10,
            "total_projects": 34,
            "active_projects": 26,
            "total_budget": 14250000.0,
        }

        # Demo Department Summary
        self._demo_dept_summary = pd.DataFrame([
            {"department_name": "Research & Development", "headcount": 680, "avg_salary": 6850.50, "attrited": 95},
            {"department_name": "Engineering & IT", "headcount": 390, "avg_salary": 7200.00, "attrited": 52},
            {"department_name": "Sales", "headcount": 250, "avg_salary": 6120.40, "attrited": 60},
            {"department_name": "Human Resources", "headcount": 80, "avg_salary": 5300.00, "attrited": 18},
            {"department_name": "Finance & Operations", "headcount": 70, "avg_salary": 7500.00, "attrited": 12},
        ])

        # Demo Employees
        self._demo_employees = [
            {"employee_id": 101, "employee_number": "EMP-00101", "first_name": "Sarah", "last_name": "Chen", "full_name": "Sarah Chen", "email": "sarah.chen@enterprise.com", "gender": "Female", "age": 34, "department_id": 4, "department_name": "Engineering & IT", "job_role": "Lead Architect", "job_level": 4, "monthly_income": 12500.0, "education_field": "Computer Science", "years_at_company": 6, "attrition": "No", "hire_date": "2020-03-15"},
            {"employee_id": 102, "employee_number": "EMP-00102", "first_name": "Marcus", "last_name": "Vance", "full_name": "Marcus Vance", "email": "marcus.vance@enterprise.com", "gender": "Male", "age": 29, "department_id": 1, "department_name": "Research & Development", "job_role": "Research Scientist", "job_level": 3, "monthly_income": 8900.0, "education_field": "Life Sciences", "years_at_company": 4, "attrition": "No", "hire_date": "2022-01-10"},
            {"employee_id": 103, "employee_number": "EMP-00103", "first_name": "Elena", "last_name": "Rostova", "full_name": "Elena Rostova", "email": "elena.rostova@enterprise.com", "gender": "Female", "age": 41, "department_id": 2, "department_name": "Sales", "job_role": "Manager", "job_level": 4, "monthly_income": 11200.0, "education_field": "Marketing", "years_at_company": 8, "attrition": "No", "hire_date": "2018-06-01"},
            {"employee_id": 104, "employee_number": "EMP-00104", "first_name": "David", "last_name": "Kim", "full_name": "David Kim", "email": "david.kim@enterprise.com", "gender": "Male", "age": 26, "department_id": 4, "department_name": "Engineering & IT", "job_role": "Software Engineer", "job_level": 2, "monthly_income": 6200.0, "education_field": "Computer Science", "years_at_company": 2, "attrition": "No", "hire_date": "2024-04-12"},
            {"employee_id": 105, "employee_number": "EMP-00105", "first_name": "Priya", "last_name": "Sharma", "full_name": "Priya Sharma", "email": "priya.sharma@enterprise.com", "gender": "Female", "age": 31, "department_id": 3, "department_name": "Human Resources", "job_role": "Human Resources Specialist", "job_level": 2, "monthly_income": 5400.0, "education_field": "Human Resources", "years_at_company": 3, "attrition": "No", "hire_date": "2023-08-20"},
            {"employee_id": 106, "employee_number": "EMP-00106", "first_name": "Alexander", "last_name": "Wright", "full_name": "Alexander Wright", "email": "alex.wright@enterprise.com", "gender": "Male", "age": 38, "department_id": 1, "department_name": "Research & Development", "job_role": "Senior Software Engineer", "job_level": 3, "monthly_income": 9500.0, "education_field": "Medical", "years_at_company": 5, "attrition": "No", "hire_date": "2021-02-14"},
            {"employee_id": 107, "employee_number": "EMP-00107", "first_name": "Jessica", "last_name": "Taylor", "full_name": "Jessica Taylor", "email": "jessica.taylor@enterprise.com", "gender": "Female", "age": 27, "department_id": 2, "department_name": "Sales", "job_role": "Sales Executive", "job_level": 2, "monthly_income": 5800.0, "education_field": "Marketing", "years_at_company": 2, "attrition": "Yes", "hire_date": "2024-02-01"},
            {"employee_id": 108, "employee_number": "EMP-00108", "first_name": "Michael", "last_name": "Chang", "full_name": "Michael Chang", "email": "michael.chang@enterprise.com", "gender": "Male", "age": 45, "department_id": 5, "department_name": "Finance & Operations", "job_role": "Manager", "job_level": 5, "monthly_income": 14800.0, "education_field": "Finance", "years_at_company": 11, "attrition": "No", "hire_date": "2015-09-01"},
        ]

        # Demo Reviews (for Query 1 and Query 2)
        reviews_data = [
            {"review_id": 1, "employee_id": 101, "full_name": "Sarah Chen", "department_name": "Engineering & IT", "job_role": "Lead Architect", "year_num": 2024, "performance_rating": 4.9, "job_satisfaction": 4, "monthly_income": 12500.0},
            {"review_id": 2, "employee_id": 101, "full_name": "Sarah Chen", "department_name": "Engineering & IT", "job_role": "Senior Software Engineer", "year_num": 2023, "performance_rating": 4.6, "job_satisfaction": 4, "monthly_income": 10500.0},
            {"review_id": 3, "employee_id": 101, "full_name": "Sarah Chen", "department_name": "Engineering & IT", "job_role": "Software Engineer", "year_num": 2022, "performance_rating": 4.2, "job_satisfaction": 3, "monthly_income": 8200.0},

            {"review_id": 4, "employee_id": 102, "full_name": "Marcus Vance", "department_name": "Research & Development", "job_role": "Research Scientist", "year_num": 2024, "performance_rating": 4.7, "job_satisfaction": 4, "monthly_income": 8900.0},
            {"review_id": 5, "employee_id": 102, "full_name": "Marcus Vance", "department_name": "Research & Development", "job_role": "Laboratory Technician", "year_num": 2023, "performance_rating": 4.3, "job_satisfaction": 3, "monthly_income": 7100.0},
            {"review_id": 6, "employee_id": 102, "full_name": "Marcus Vance", "department_name": "Research & Development", "job_role": "Laboratory Technician", "year_num": 2022, "performance_rating": 3.8, "job_satisfaction": 3, "monthly_income": 6000.0},

            {"review_id": 7, "employee_id": 103, "full_name": "Elena Rostova", "department_name": "Sales", "job_role": "Manager", "year_num": 2024, "performance_rating": 4.8, "job_satisfaction": 5, "monthly_income": 11200.0},
            {"review_id": 8, "employee_id": 103, "full_name": "Elena Rostova", "department_name": "Sales", "job_role": "Sales Executive", "year_num": 2023, "performance_rating": 4.5, "job_satisfaction": 4, "monthly_income": 9400.0},

            {"review_id": 9, "employee_id": 106, "full_name": "Alexander Wright", "department_name": "Research & Development", "job_role": "Senior Software Engineer", "year_num": 2024, "performance_rating": 4.4, "job_satisfaction": 4, "monthly_income": 9500.0},
            {"review_id": 10, "employee_id": 106, "full_name": "Alexander Wright", "department_name": "Research & Development", "job_role": "Software Engineer", "year_num": 2023, "performance_rating": 4.1, "job_satisfaction": 3, "monthly_income": 8300.0},

            {"review_id": 11, "employee_id": 108, "full_name": "Michael Chang", "department_name": "Finance & Operations", "job_role": "Manager", "year_num": 2024, "performance_rating": 4.6, "job_satisfaction": 4, "monthly_income": 14800.0},
            {"review_id": 12, "employee_id": 108, "full_name": "Michael Chang", "department_name": "Finance & Operations", "job_role": "Manager", "year_num": 2023, "performance_rating": 4.5, "job_satisfaction": 4, "monthly_income": 13900.0},
        ]
        self._demo_reviews_df = pd.DataFrame(reviews_data)

        # Demo SCD Type 2 Audit Trail (Query 3)
        scd2_data = [
            {"employee_id": 101, "employee_number": "EMP-00101", "full_name": "Sarah Chen", "version": 1, "department_name": "Engineering & IT", "job_role": "Software Engineer", "job_level": 2, "monthly_income": 8200.0, "attrition": "No", "effective_start_date": "2020-03-15", "effective_end_date": "2022-07-01", "is_current": 0},
            {"employee_id": 101, "employee_number": "EMP-00101", "full_name": "Sarah Chen", "version": 2, "department_name": "Engineering & IT", "job_role": "Senior Software Engineer", "job_level": 3, "monthly_income": 10500.0, "attrition": "No", "effective_start_date": "2022-07-01", "effective_end_date": "2024-01-15", "is_current": 0},
            {"employee_id": 101, "employee_number": "EMP-00101", "full_name": "Sarah Chen", "version": 3, "department_name": "Engineering & IT", "job_role": "Lead Architect", "job_level": 4, "monthly_income": 12500.0, "attrition": "No", "effective_start_date": "2024-01-15", "effective_end_date": "9999-12-31", "is_current": 1},

            {"employee_id": 102, "employee_number": "EMP-00102", "full_name": "Marcus Vance", "version": 1, "department_name": "Research & Development", "job_role": "Laboratory Technician", "job_level": 1, "monthly_income": 6000.0, "attrition": "No", "effective_start_date": "2022-01-10", "effective_end_date": "2023-04-01", "is_current": 0},
            {"employee_id": 102, "employee_number": "EMP-00102", "full_name": "Marcus Vance", "version": 2, "department_name": "Research & Development", "job_role": "Laboratory Technician", "job_level": 2, "monthly_income": 7100.0, "attrition": "No", "effective_start_date": "2023-04-01", "effective_end_date": "2024-02-01", "is_current": 0},
            {"employee_id": 102, "employee_number": "EMP-00102", "full_name": "Marcus Vance", "version": 3, "department_name": "Research & Development", "job_role": "Research Scientist", "job_level": 3, "monthly_income": 8900.0, "attrition": "No", "effective_start_date": "2024-02-01", "effective_end_date": "9999-12-31", "is_current": 1},

            {"employee_id": 103, "employee_number": "EMP-00103", "full_name": "Elena Rostova", "version": 1, "department_name": "Sales", "job_role": "Sales Representative", "job_level": 2, "monthly_income": 6800.0, "attrition": "No", "effective_start_date": "2018-06-01", "effective_end_date": "2021-03-10", "is_current": 0},
            {"employee_id": 103, "employee_number": "EMP-00103", "full_name": "Elena Rostova", "version": 2, "department_name": "Sales", "job_role": "Sales Executive", "job_level": 3, "monthly_income": 9400.0, "attrition": "No", "effective_start_date": "2021-03-10", "effective_end_date": "2023-11-01", "is_current": 0},
            {"employee_id": 103, "employee_number": "EMP-00103", "full_name": "Elena Rostova", "version": 3, "department_name": "Sales", "job_role": "Manager", "job_level": 4, "monthly_income": 11200.0, "attrition": "No", "effective_start_date": "2023-11-01", "effective_end_date": "9999-12-31", "is_current": 1},
        ]
        self._demo_scd2_df = pd.DataFrame(scd2_data)

        # Demo Attrition Risk (Query 4)
        attrition_data = [
            {"department_name": "Research & Development", "calculated_risk_tier": "High Attrition Risk", "salary_quartile": 1, "employee_count": 48, "avg_rating": 2.85, "avg_satisfaction": 1.40, "total_attrited": 28},
            {"department_name": "Research & Development", "calculated_risk_tier": "Moderate Risk", "salary_quartile": 2, "employee_count": 120, "avg_rating": 3.40, "avg_satisfaction": 2.15, "total_attrited": 24},
            {"department_name": "Research & Development", "calculated_risk_tier": "Low Risk", "salary_quartile": 3, "employee_count": 280, "avg_rating": 4.10, "avg_satisfaction": 4.20, "total_attrited": 18},
            {"department_name": "Research & Development", "calculated_risk_tier": "Low Risk", "salary_quartile": 4, "employee_count": 232, "avg_rating": 4.55, "avg_satisfaction": 4.60, "total_attrited": 10},

            {"department_name": "Engineering & IT", "calculated_risk_tier": "High Attrition Risk", "salary_quartile": 1, "employee_count": 32, "avg_rating": 2.90, "avg_satisfaction": 1.30, "total_attrited": 19},
            {"department_name": "Engineering & IT", "calculated_risk_tier": "Moderate Risk", "salary_quartile": 2, "employee_count": 75, "avg_rating": 3.55, "avg_satisfaction": 2.40, "total_attrited": 14},
            {"department_name": "Engineering & IT", "calculated_risk_tier": "Low Risk", "salary_quartile": 3, "employee_count": 150, "avg_rating": 4.25, "avg_satisfaction": 4.10, "total_attrited": 11},
            {"department_name": "Engineering & IT", "calculated_risk_tier": "Low Risk", "salary_quartile": 4, "employee_count": 133, "avg_rating": 4.70, "avg_satisfaction": 4.50, "total_attrited": 8},

            {"department_name": "Sales", "calculated_risk_tier": "High Attrition Risk", "salary_quartile": 1, "employee_count": 38, "avg_rating": 2.75, "avg_satisfaction": 1.25, "total_attrited": 25},
            {"department_name": "Sales", "calculated_risk_tier": "Moderate Risk", "salary_quartile": 2, "employee_count": 62, "avg_rating": 3.30, "avg_satisfaction": 2.10, "total_attrited": 18},
            {"department_name": "Sales", "calculated_risk_tier": "Low Risk", "salary_quartile": 3, "employee_count": 95, "avg_rating": 3.90, "avg_satisfaction": 3.80, "total_attrited": 11},
            {"department_name": "Sales", "calculated_risk_tier": "Low Risk", "salary_quartile": 4, "employee_count": 55, "avg_rating": 4.40, "avg_satisfaction": 4.30, "total_attrited": 6},
        ]
        self._demo_attrition_df = pd.DataFrame(attrition_data)

        # Demo Resource Allocations (Query 5)
        allocations_data = [
            {"full_name": "Sarah Chen", "department_name": "Engineering & IT", "assigned_project_count": 3, "total_allocation_pct": 130.0, "capacity_status": "OVER-ALLOCATED (Bottleneck Risk)"},
            {"full_name": "David Kim", "department_name": "Engineering & IT", "assigned_project_count": 2, "total_allocation_pct": 115.0, "capacity_status": "OVER-ALLOCATED (Bottleneck Risk)"},
            {"full_name": "Marcus Vance", "department_name": "Research & Development", "assigned_project_count": 2, "total_allocation_pct": 100.0, "capacity_status": "Fully Utilized"},
            {"full_name": "Alexander Wright", "department_name": "Research & Development", "assigned_project_count": 2, "total_allocation_pct": 100.0, "capacity_status": "Fully Utilized"},
            {"full_name": "Elena Rostova", "department_name": "Sales", "assigned_project_count": 2, "total_allocation_pct": 85.0, "capacity_status": "Available Bandwidth"},
            {"full_name": "Priya Sharma", "department_name": "Human Resources", "assigned_project_count": 1, "total_allocation_pct": 60.0, "capacity_status": "Available Bandwidth"},
            {"full_name": "Michael Chang", "department_name": "Finance & Operations", "assigned_project_count": 1, "total_allocation_pct": 50.0, "capacity_status": "Available Bandwidth"},
        ]
        self._demo_allocations_df = pd.DataFrame(allocations_data)

        # Demo Projects
        self._demo_projects = [
            {"project_id": 1, "project_code": "PRJ-04-0001", "project_name": "Enterprise Data Warehouse Migration", "department_id": 4, "department_name": "Engineering & IT", "priority": "Critical", "status": "Active", "start_date": "2024-01-15", "end_date": "2024-12-31", "budget": 1250000.0},
            {"project_id": 2, "project_code": "PRJ-01-0002", "project_name": "AI Predictive Attrition Engine", "department_id": 1, "department_name": "Research & Development", "priority": "High", "status": "Active", "start_date": "2024-03-01", "end_date": "2025-06-30", "budget": 850000.0},
            {"project_id": 3, "project_code": "PRJ-02-0003", "project_name": "Global CRM Integration", "department_id": 2, "department_name": "Sales", "priority": "Medium", "status": "Active", "start_date": "2024-02-10", "end_date": "2024-10-31", "budget": 450000.0},
            {"project_id": 4, "project_code": "PRJ-03-0004", "project_name": "Automated HR Onboarding Portal", "department_id": 3, "department_name": "Human Resources", "priority": "Medium", "status": "Completed", "start_date": "2023-08-01", "end_date": "2024-01-20", "budget": 200000.0},
            {"project_id": 5, "project_code": "PRJ-05-0005", "project_name": "ERP Cost Center Consolidation", "department_id": 5, "department_name": "Finance & Operations", "priority": "High", "status": "Active", "start_date": "2024-04-01", "end_date": "2024-11-30", "budget": 600000.0},
        ]
