"""
Project Entity Class
Encapsulates project state, operational lifecycle, and budget constraints.
"""

from datetime import date, datetime
from typing import Optional, Dict, Any
from decimal import Decimal


class Project:
    """
    Represents an enterprise project.
    Encapsulates lifecycle transitions, priority settings, and financial allocations.
    """

    VALID_PRIORITIES = {"Low", "Medium", "High", "Critical"}
    VALID_STATUSES = {"Planning", "Active", "On Hold", "Completed", "Cancelled"}

    def __init__(
        self,
        project_name: str,
        department_id: int,
        project_code: Optional[str] = None,
        priority: str = "Medium",
        status: str = "Active",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        budget: float = 0.0,
        project_id: Optional[int] = None,
        created_at: Optional[datetime] = None,
    ):
        self.project_id = project_id
        self.project_code = project_code.strip() if project_code else ""
        self.project_name = project_name.strip() if project_name else ""
        self.department_id = department_id
        self.priority = priority
        self.status = status
        self.start_date = start_date or date.today()
        self.end_date = end_date
        self._budget = Decimal(str(budget))
        self.created_at = created_at

        self.validate()

    @property
    def budget(self) -> float:
        """Returns the current allocated budget."""
        return float(self._budget)

    @budget.setter
    def budget(self, value: float):
        """Sets project budget ensuring it remains non-negative."""
        decimal_val = Decimal(str(value))
        if decimal_val < 0:
            raise ValueError("Project budget cannot be negative.")
        self._budget = decimal_val

    @property
    def is_active(self) -> bool:
        """Checks if the project is actively in flight."""
        return self.status == "Active"

    def validate(self) -> bool:
        """Validates project business rules."""
        if not self.project_name:
            raise ValueError("Project name cannot be empty.")

        if self.department_id <= 0:
            raise ValueError("Invalid department ID assigned to project.")

        if self.priority not in self.VALID_PRIORITIES:
            raise ValueError(f"Priority must be one of {self.VALID_PRIORITIES}. Received: {self.priority}")

        if self.status not in self.VALID_STATUSES:
            raise ValueError(f"Status must be one of {self.VALID_STATUSES}. Received: {self.status}")

        if self._budget < 0:
            raise ValueError("Budget cannot be negative.")

        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValueError("Project end date cannot be earlier than start date.")

        return True

    def update_status(self, new_status: str):
        """Transitions project lifecycle state."""
        if new_status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid project status: {new_status}. Allowed: {self.VALID_STATUSES}")
        self.status = new_status
        if new_status == "Completed" and not self.end_date:
            self.end_date = date.today()

    def adjust_budget(self, delta_amount: float):
        """Adjusts the budget by an incremental amount (+ or -)."""
        new_val = self._budget + Decimal(str(delta_amount))
        if new_val < 0:
            raise ValueError(f"Cannot adjust budget below zero. Result would be {new_val}.")
        self._budget = new_val

    def duration_days(self) -> Optional[int]:
        """Calculates project duration in days if end date is set."""
        if self.end_date and self.start_date:
            return (self.end_date - self.start_date).days
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes project instance to a dictionary."""
        return {
            "project_id": self.project_id,
            "project_code": self.project_code,
            "project_name": self.project_name,
            "department_id": self.department_id,
            "priority": self.priority,
            "status": self.status,
            "is_active": self.is_active,
            "start_date": str(self.start_date) if self.start_date else None,
            "end_date": str(self.end_date) if self.end_date else None,
            "budget": self.budget,
            "created_at": str(self.created_at) if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        """Builds a Project instance from a database row dictionary."""
        start_d = data.get("start_date")
        if isinstance(start_d, str):
            start_d = datetime.strptime(start_d, "%Y-%m-%d").date()

        end_d = data.get("end_date")
        if isinstance(end_d, str):
            end_d = datetime.strptime(end_d, "%Y-%m-%d").date()

        return cls(
            project_id=data.get("project_id"),
            project_code=data.get("project_code"),
            project_name=data.get("project_name", ""),
            department_id=data.get("department_id", 1),
            priority=data.get("priority", "Medium"),
            status=data.get("status", "Active"),
            start_date=start_d,
            end_date=end_d,
            budget=float(data.get("budget", 0.0)),
            created_at=data.get("created_at"),
        )

    def __repr__(self) -> str:
        return f"<Project [{self.project_code or 'NEW'}] '{self.project_name}' ({self.status}, ${self.budget:,.2f})>"
