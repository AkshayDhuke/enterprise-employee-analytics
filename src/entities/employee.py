"""
Employee Entity Class
Encapsulates employee state, validation rules, and business behaviors.
"""

from datetime import date, datetime
from typing import Optional, Dict, Any
from decimal import Decimal


class Employee:
    """
    Represents an employee within the enterprise system.
    Encapsulates core attributes, data validation, and business domain logic.
    """

    VALID_GENDERS = {"Male", "Female", "Non-Binary", "Other"}
    VALID_ATTRITION = {"Yes", "No"}
    MIN_JOB_LEVEL = 1
    MAX_JOB_LEVEL = 5

    def __init__(
        self,
        first_name: str,
        last_name: str,
        email: str,
        department_id: int,
        job_role: str,
        monthly_income: float,
        hire_date: Optional[date] = None,
        employee_id: Optional[int] = None,
        employee_number: Optional[str] = None,
        gender: Optional[str] = "Other",
        age: Optional[int] = 25,
        job_level: int = 1,
        education_field: Optional[str] = "Life Sciences",
        years_at_company: int = 0,
        attrition: str = "No",
        updated_at: Optional[datetime] = None,
    ):
        self.employee_id = employee_id
        self.employee_number = employee_number
        self.first_name = first_name.strip() if first_name else ""
        self.last_name = last_name.strip() if last_name else ""
        self.email = email.strip().lower() if email else ""
        self.gender = gender
        self.age = age
        self.department_id = department_id
        self.job_role = job_role.strip() if job_role else ""
        self.job_level = job_level
        self._monthly_income = Decimal(str(monthly_income))
        self.education_field = education_field
        self.years_at_company = years_at_company
        self.attrition = attrition
        self.hire_date = hire_date or date.today()
        self.updated_at = updated_at

        # Validate immediately on initialization
        self.validate()

    @property
    def full_name(self) -> str:
        """Returns the full combined employee name."""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def monthly_income(self) -> float:
        """Monthly salary getter."""
        return float(self._monthly_income)

    @monthly_income.setter
    def monthly_income(self, value: float):
        """Monthly salary setter with positive boundary check."""
        decimal_val = Decimal(str(value))
        if decimal_val < 0:
            raise ValueError("Monthly income cannot be negative.")
        self._monthly_income = decimal_val

    @property
    def annual_salary(self) -> float:
        """Calculates total annual gross salary."""
        return float(self._monthly_income * 12)

    def validate(self) -> bool:
        """Validates all business constraints for an Employee instance."""
        if not self.first_name or not self.last_name:
            raise ValueError("Employee must have both a first name and a last name.")

        if not self.email or "@" not in self.email:
            raise ValueError(f"Invalid email address provided: {self.email}")

        if self.age is not None and (self.age < 18 or self.age > 100):
            raise ValueError(f"Employee age must be between 18 and 100. Received: {self.age}")

        if not (self.MIN_JOB_LEVEL <= self.job_level <= self.MAX_JOB_LEVEL):
            raise ValueError(
                f"Job level must be between {self.MIN_JOB_LEVEL} and {self.MAX_JOB_LEVEL}. Received: {self.job_level}"
            )

        if self._monthly_income < 0:
            raise ValueError("Monthly income cannot be negative.")

        if self.attrition not in self.VALID_ATTRITION:
            raise ValueError(f"Attrition must be one of {self.VALID_ATTRITION}. Received: {self.attrition}")

        return True

    def promote(self, new_role: str, new_level: int, salary_increment_pct: float = 10.0):
        """
        Executes an employee promotion behavior.
        Increments job level, applies salary increment, and updates job title.
        """
        if new_level <= self.job_level:
            raise ValueError(f"New job level ({new_level}) must be higher than current level ({self.job_level}).")
        if new_level > self.MAX_JOB_LEVEL:
            raise ValueError(f"Job level cannot exceed maximum of {self.MAX_JOB_LEVEL}.")

        self.job_role = new_role
        self.job_level = new_level
        increment = self._monthly_income * (Decimal(str(salary_increment_pct)) / Decimal("100"))
        self._monthly_income += increment

    def transfer_department(self, new_department_id: int):
        """Transfers the employee to a new department."""
        if new_department_id <= 0:
            raise ValueError("Department ID must be a positive integer.")
        self.department_id = new_department_id

    def record_attrition(self):
        """Marks the employee as attrited/departed from the organization."""
        self.attrition = "Yes"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the employee object into a dictionary for database persistence or UI display."""
        return {
            "employee_id": self.employee_id,
            "employee_number": self.employee_number,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "email": self.email,
            "gender": self.gender,
            "age": self.age,
            "department_id": self.department_id,
            "job_role": self.job_role,
            "job_level": self.job_level,
            "monthly_income": self.monthly_income,
            "annual_salary": self.annual_salary,
            "education_field": self.education_field,
            "years_at_company": self.years_at_company,
            "attrition": self.attrition,
            "hire_date": str(self.hire_date) if self.hire_date else None,
            "updated_at": str(self.updated_at) if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Employee":
        """Instantiates an Employee from a database row dictionary."""
        hire_d = data.get("hire_date")
        if isinstance(hire_d, str):
            hire_d = datetime.strptime(hire_d, "%Y-%m-%d").date()

        return cls(
            employee_id=data.get("employee_id"),
            employee_number=data.get("employee_number"),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            email=data.get("email", ""),
            gender=data.get("gender", "Other"),
            age=data.get("age", 25),
            department_id=data.get("department_id", 1),
            job_role=data.get("job_role", ""),
            job_level=data.get("job_level", 1),
            monthly_income=float(data.get("monthly_income", 0.0)),
            education_field=data.get("education_field", ""),
            years_at_company=data.get("years_at_company", 0),
            attrition=data.get("attrition", "No"),
            hire_date=hire_d,
            updated_at=data.get("updated_at"),
        )

    def __repr__(self) -> str:
        return f"<Employee #{self.employee_id or 'NEW'} {self.full_name} ({self.job_role}, Lvl {self.job_level})>"
