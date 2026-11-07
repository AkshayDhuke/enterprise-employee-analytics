"""
Entity Models Package
Encapsulates domain entities: Employee, Project, and Review.
"""

from src.entities.employee import Employee
from src.entities.project import Project
from src.entities.review import Review

__all__ = ["Employee", "Project", "Review"]
