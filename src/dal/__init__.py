"""
Data Access Layer (DAL) Package
Exposes managers for CRUD operations and Star Schema analytical reporting.
"""

from src.dal.base_manager import BaseManager
from src.dal.employee_manager import EmployeeManager
from src.dal.project_manager import ProjectManager
from src.dal.review_manager import ReviewManager
from src.dal.analytics_manager import AnalyticsManager

__all__ = [
    "BaseManager",
    "EmployeeManager",
    "ProjectManager",
    "ReviewManager",
    "AnalyticsManager",
]
