"""
Performance Review Entity Class
Encapsulates employee review cycles, rating distributions, and attrition risk evaluation.
"""

from datetime import date, datetime
from typing import Optional, Dict, Any


class Review:
    """
    Represents an employee performance review record.
    Encapsulates multidimensional scores (performance, work-life balance, job satisfaction)
    and risk tier diagnostics.
    """

    MIN_RATING = 1
    MAX_RATING = 5
    MIN_METRIC_4 = 1
    MAX_METRIC_4 = 4

    def __init__(
        self,
        employee_id: int,
        review_date: Optional[date] = None,
        review_cycle: Optional[str] = None,
        performance_rating: int = 3,
        work_life_balance: int = 3,
        job_satisfaction: int = 3,
        training_times_last_year: int = 0,
        reviewer_comments: Optional[str] = "",
        review_id: Optional[int] = None,
        created_at: Optional[datetime] = None,
    ):
        self.review_id = review_id
        self.employee_id = employee_id
        self.review_date = review_date or date.today()
        self.review_cycle = review_cycle or f"{self.review_date.year}-Q{(self.review_date.month - 1) // 3 + 1}"
        self.performance_rating = int(performance_rating)
        self.work_life_balance = int(work_life_balance)
        self.job_satisfaction = int(job_satisfaction)
        self.training_times_last_year = max(0, int(training_times_last_year))
        self.reviewer_comments = reviewer_comments or ""
        self.created_at = created_at

        self.validate()

    def validate(self) -> bool:
        """Enforces database CHECK constraints on rating scales."""
        if self.employee_id <= 0:
            raise ValueError("Employee ID must be a valid positive integer.")

        if not (self.MIN_RATING <= self.performance_rating <= self.MAX_RATING):
            raise ValueError(
                f"Performance rating must be between {self.MIN_RATING} and {self.MAX_RATING}. "
                f"Received: {self.performance_rating}"
            )

        if not (self.MIN_METRIC_4 <= self.work_life_balance <= self.MAX_METRIC_4):
            raise ValueError(
                f"Work-Life balance score must be between {self.MIN_METRIC_4} and {self.MAX_METRIC_4}. "
                f"Received: {self.work_life_balance}"
            )

        if not (self.MIN_METRIC_4 <= self.job_satisfaction <= self.MAX_METRIC_4):
            raise ValueError(
                f"Job satisfaction score must be between {self.MIN_METRIC_4} and {self.MAX_METRIC_4}. "
                f"Received: {self.job_satisfaction}"
            )

        return True

    @property
    def is_top_performer(self) -> bool:
        """Returns True if the employee achieved an exemplary rating of 4 or 5."""
        return self.performance_rating >= 4

    @property
    def composite_score(self) -> float:
        """
        Calculates a normalized 100-point composite talent score:
        - 50% weight on Performance Rating (1-5 scaled to 0-50)
        - 25% weight on Job Satisfaction (1-4 scaled to 0-25)
        - 25% weight on Work-Life Balance (1-4 scaled to 0-25)
        """
        perf_component = (self.performance_rating / 5.0) * 50.0
        sat_component = (self.job_satisfaction / 4.0) * 25.0
        wlb_component = (self.work_life_balance / 4.0) * 25.0
        return round(perf_component + sat_component + wlb_component, 2)

    @property
    def attrition_risk_tier(self) -> str:
        """
        Diagnoses attrition risk consistent with Data Warehouse analytical logic:
        - High Attrition Risk: Both work_life_balance and job_satisfaction == 1
        - Moderate Risk: Either work_life_balance <= 2 OR job_satisfaction <= 2
        - Low Risk: Healthy sentiment across both metrics
        """
        if self.work_life_balance == 1 and self.job_satisfaction == 1:
            return "High Attrition Risk"
        elif self.work_life_balance <= 2 or self.job_satisfaction <= 2:
            return "Moderate Risk"
        return "Low Risk"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes Review to a dictionary."""
        return {
            "review_id": self.review_id,
            "employee_id": self.employee_id,
            "review_date": str(self.review_date),
            "review_cycle": self.review_cycle,
            "performance_rating": self.performance_rating,
            "work_life_balance": self.work_life_balance,
            "job_satisfaction": self.job_satisfaction,
            "training_times_last_year": self.training_times_last_year,
            "composite_score": self.composite_score,
            "attrition_risk_tier": self.attrition_risk_tier,
            "is_top_performer": self.is_top_performer,
            "reviewer_comments": self.reviewer_comments,
            "created_at": str(self.created_at) if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Review":
        """Instantiates Review from a database record."""
        rev_d = data.get("review_date")
        if isinstance(rev_d, str):
            rev_d = datetime.strptime(rev_d, "%Y-%m-%d").date()

        return cls(
            review_id=data.get("review_id"),
            employee_id=data.get("employee_id"),
            review_date=rev_d,
            review_cycle=data.get("review_cycle"),
            performance_rating=data.get("performance_rating", 3),
            work_life_balance=data.get("work_life_balance", 3),
            job_satisfaction=data.get("job_satisfaction", 3),
            training_times_last_year=data.get("training_times_last_year", 0),
            reviewer_comments=data.get("reviewer_comments", ""),
            created_at=data.get("created_at"),
        )

    def __repr__(self) -> str:
        return f"<Review #{self.review_id or 'NEW'} Emp #{self.employee_id} [{self.review_cycle}] Rating: {self.performance_rating}/5>"
