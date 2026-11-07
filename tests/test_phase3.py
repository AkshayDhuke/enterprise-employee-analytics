"""
Phase 3 Verification & Unit Test Suite
Validates Singleton Design Pattern, Entity encapsulation & behaviors,
and Data Access Layer (DAL) inheritance and methods.
"""

import unittest
import threading
from datetime import date
from decimal import Decimal

from unittest.mock import MagicMock, patch

# Import Phase 3 modules
from src.db_manager import DatabaseConnection
from src.entities.employee import Employee
from src.entities.project import Project
from src.entities.review import Review
from src.dal.base_manager import BaseManager
from src.dal.employee_manager import EmployeeManager
from src.dal.project_manager import ProjectManager
from src.dal.review_manager import ReviewManager
from src.dal.analytics_manager import AnalyticsManager


class TestSingletonPattern(unittest.TestCase):
    """Verifies Singleton Design Pattern for DatabaseConnection."""

    def test_singleton_identity(self):
        """Tests that multiple instantiations yield the exact same instance."""
        db1 = DatabaseConnection()
        db2 = DatabaseConnection()
        self.assertIs(db1, db2, "DatabaseConnection must follow the Singleton pattern (same instance).")

    def test_singleton_multithreading(self):
        """Tests thread-safety of the Singleton instantiation."""
        instances = []

        def worker():
            inst = DatabaseConnection()
            instances.append(inst)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        first_instance = instances[0]
        for inst in instances:
            self.assertIs(inst, first_instance, "Thread safe singleton check failed across threads.")


class TestEntityEncapsulation(unittest.TestCase):
    """Verifies OOP encapsulation, attributes, and behaviors of Entity classes."""

    def test_employee_entity_behaviors(self):
        """Tests Employee validation, properties, promotion, and serialization."""
        emp = Employee(
            first_name="Jane",
            last_name="Doe",
            email="jane.doe@enterprise.com",
            department_id=1,
            job_role="Software Engineer",
            monthly_income=7500.0,
            job_level=2,
            age=29,
        )

        # Check properties
        self.assertEqual(emp.full_name, "Jane Doe")
        self.assertEqual(emp.annual_salary, 90000.0)

        # Test promotion behavior
        emp.promote(new_role="Senior Software Engineer", new_level=3, salary_increment_pct=10.0)
        self.assertEqual(emp.job_role, "Senior Software Engineer")
        self.assertEqual(emp.job_level, 3)
        self.assertEqual(emp.monthly_income, 8250.0)

        # Test validation bounds
        with self.assertRaises(ValueError):
            emp.monthly_income = -500.0

        with self.assertRaises(ValueError):
            Employee("Bad", "User", "invalid-email", 1, "Role", 5000.0)

        # Test dictionary serialization and deserialization
        data = emp.to_dict()
        self.assertEqual(data["full_name"], "Jane Doe")
        recreated = Employee.from_dict(data)
        self.assertEqual(recreated.full_name, emp.full_name)

    def test_project_entity_behaviors(self):
        """Tests Project validation, status transitions, and budget controls."""
        proj = Project(
            project_code="PRJ-01-9999",
            project_name="AI Agent Migration",
            department_id=1,
            priority="Critical",
            status="Active",
            budget=150000.0,
        )

        self.assertTrue(proj.is_active)
        proj.adjust_budget(50000.0)
        self.assertEqual(proj.budget, 200000.0)

        proj.update_status("Completed")
        self.assertEqual(proj.status, "Completed")
        self.assertFalse(proj.is_active)
        self.assertIsNotNone(proj.end_date)

        # Test invalid status
        with self.assertRaises(ValueError):
            proj.update_status("UnknownStatus")

    def test_review_entity_behaviors(self):
        """Tests Review composite score calculation and risk diagnostics."""
        # Top performer with low risk
        top_rev = Review(
            employee_id=101,
            performance_rating=5,
            work_life_balance=4,
            job_satisfaction=4,
            reviewer_comments="Outstanding output.",
        )
        self.assertTrue(top_rev.is_top_performer)
        self.assertEqual(top_rev.composite_score, 100.0)
        self.assertEqual(top_rev.attrition_risk_tier, "Low Risk")

        # High attrition risk case (balance=1, satisfaction=1)
        burnout_rev = Review(
            employee_id=102,
            performance_rating=3,
            work_life_balance=1,
            job_satisfaction=1,
            reviewer_comments="Needs urgent workload adjustment.",
        )
        self.assertFalse(burnout_rev.is_top_performer)
        self.assertEqual(burnout_rev.attrition_risk_tier, "High Attrition Risk")

        # Test constraint validation
        with self.assertRaises(ValueError):
            Review(employee_id=103, performance_rating=6)  # Exceeds max 5


class TestDALInheritanceAndStructure(unittest.TestCase):
    """Verifies that DAL Managers inherit from DatabaseConnection and implement required methods."""

    def test_inheritance_hierarchy(self):
        """Verifies manager classes inherit from DatabaseConnection."""
        self.assertTrue(issubclass(BaseManager, DatabaseConnection))
        self.assertTrue(issubclass(EmployeeManager, BaseManager))
        self.assertTrue(issubclass(EmployeeManager, DatabaseConnection))
        self.assertTrue(issubclass(ProjectManager, BaseManager))
        self.assertTrue(issubclass(ReviewManager, BaseManager))
        self.assertTrue(issubclass(AnalyticsManager, BaseManager))
        self.assertTrue(issubclass(AnalyticsManager, DatabaseConnection))

    def test_manager_methods_exist(self):
        """Ensures all required CRUD and Analytical methods exist."""
        emp_mgr = EmployeeManager()
        self.assertTrue(hasattr(emp_mgr, "create_employee"))
        self.assertTrue(hasattr(emp_mgr, "get_employee_by_id"))
        self.assertTrue(hasattr(emp_mgr, "update_employee_scd2"))

        proj_mgr = ProjectManager()
        self.assertTrue(hasattr(proj_mgr, "create_project"))
        self.assertTrue(hasattr(proj_mgr, "assign_employee_to_project"))

        rev_mgr = ReviewManager()
        self.assertTrue(hasattr(rev_mgr, "create_review"))
        self.assertTrue(hasattr(rev_mgr, "get_recent_reviews"))

        analytics_mgr = AnalyticsManager()
        self.assertTrue(hasattr(analytics_mgr, "get_top_performers_by_department"))
        self.assertTrue(hasattr(analytics_mgr, "get_yoy_performance_trajectory"))
        self.assertTrue(hasattr(analytics_mgr, "get_scd2_audit_trail"))
        self.assertTrue(hasattr(analytics_mgr, "get_attrition_risk_analysis"))
        self.assertTrue(hasattr(analytics_mgr, "get_resource_bottlenecks"))
        self.assertTrue(hasattr(analytics_mgr, "get_executive_kpis"))


class TestManagerOperationsMocked(unittest.TestCase):
    """Verifies manager CRUD logic and query formatting using mocked execution contexts."""

    @patch.object(EmployeeManager, "execute_query")
    def test_get_employee_by_id(self, mock_exec_query):
        mock_exec_query.return_value = [
            {
                "employee_id": 42,
                "employee_number": "EMP-00042",
                "first_name": "Alice",
                "last_name": "Smith",
                "email": "alice.smith@enterprise.com",
                "gender": "Female",
                "age": 31,
                "department_id": 2,
                "job_role": "Data Scientist",
                "job_level": 3,
                "monthly_income": 9500.0,
                "education_field": "Computer Science",
                "years_at_company": 4,
                "attrition": "No",
                "hire_date": "2021-04-15",
                "updated_at": None,
            }
        ]

        emp_mgr = EmployeeManager()
        emp = emp_mgr.get_employee_by_id(42)

        self.assertIsNotNone(emp)
        self.assertEqual(emp.full_name, "Alice Smith")
        self.assertEqual(emp.job_role, "Data Scientist")
        self.assertEqual(emp.annual_salary, 114000.0)
        mock_exec_query.assert_called_once()

    @patch.object(ProjectManager, "execute_query")
    def test_get_project_assignments(self, mock_exec_query):
        mock_exec_query.return_value = [
            {
                "assignment_id": 1,
                "employee_id": 42,
                "employee_name": "Alice Smith",
                "employee_number": "EMP-00042",
                "assigned_role": "Lead Data Scientist",
                "allocation_pct": 80,
                "assigned_date": "2024-01-10",
                "released_date": None,
            }
        ]

        proj_mgr = ProjectManager()
        assignments = proj_mgr.get_project_assignments(1)
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0]["allocation_pct"], 80)
        self.assertEqual(assignments[0]["assigned_role"], "Lead Data Scientist")

    @patch.object(AnalyticsManager, "execute_query")
    def test_analytics_top_performers(self, mock_exec_query):
        mock_exec_query.return_value = [
            {
                "dept_rank": 1,
                "year_num": 2024,
                "department_name": "Research & Development",
                "full_name": "Alice Smith",
                "job_role": "Data Scientist",
                "performance_rating": 5,
                "job_satisfaction": 4,
                "monthly_income": 9500.0,
            }
        ]

        analytics_mgr = AnalyticsManager()
        top_list = analytics_mgr.get_top_performers_by_department(department_name="Research & Development", top_n=1)
        self.assertEqual(len(top_list), 1)
        self.assertEqual(top_list[0]["dept_rank"], 1)
        self.assertEqual(top_list[0]["performance_rating"], 5)


if __name__ == "__main__":
    unittest.main()
