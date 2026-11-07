"""
Review Manager Class (Data Access Layer)
Handles CRUD operations for employee performance reviews and Star Schema Fact table loading.
"""

from datetime import date
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.dal.base_manager import BaseManager
from src.entities.review import Review


class ReviewManager(BaseManager):
    """
    Manages persistence of performance reviews in OLTP and synchronizes
    point-in-time records into enterprise_dw.Fact_PerformanceReviews.
    """

    def create_review(self, review: Review) -> int:
        """
        Inserts a new performance review in enterprise_oltp.performance_reviews.
        Synchronizes point-in-time snapshot with Fact_PerformanceReviews in the Data Warehouse.
        """
        review.validate()

        insert_sql = """
            INSERT INTO performance_reviews (
                employee_id, review_date, review_cycle, performance_rating,
                work_life_balance, job_satisfaction, training_times_last_year,
                reviewer_comments
            ) VALUES (
                :employee_id, :review_date, :review_cycle, :performance_rating,
                :work_life_balance, :job_satisfaction, :training_times_last_year,
                :reviewer_comments
            );
        """
        params = {
            "employee_id": review.employee_id,
            "review_date": str(review.review_date),
            "review_cycle": review.review_cycle,
            "performance_rating": review.performance_rating,
            "work_life_balance": review.work_life_balance,
            "job_satisfaction": review.job_satisfaction,
            "training_times_last_year": review.training_times_last_year,
            "reviewer_comments": review.reviewer_comments,
        }

        try:
            with self.get_oltp_connection() as conn:
                res = conn.execute(text(insert_sql), params)
                review_id = res.lastrowid
                review.review_id = review_id
                self.logger.info("Created Review #%s for Employee #%s", review_id, review.employee_id)

                # Sync to Fact_PerformanceReviews in enterprise_dw
                self._sync_review_to_dw(review)
                return review_id
        except SQLAlchemyError as err:
            self.logger.error("Failed to insert review for emp #%s: %s", review.employee_id, err)
            raise RuntimeError(f"Database error creating performance review: {err}") from err

    def _sync_review_to_dw(self, review: Review):
        """
        Performs point-in-time join matching review date within SCD2 validity interval
        and inserts into Fact_PerformanceReviews.
        """
        try:
            date_key = review.review_date.year * 10000 + review.review_date.month * 100 + review.review_date.day
            dw_sql = """
                INSERT INTO Fact_PerformanceReviews (
                    review_id, employee_sk, department_sk, review_date_key,
                    performance_rating, work_life_balance, job_satisfaction,
                    training_times_last_year, monthly_income
                )
                SELECT 
                    :review_id,
                    de.employee_sk,
                    dd.department_sk,
                    :date_key,
                    :rating,
                    :wlb,
                    :satisfaction,
                    :training,
                    de.monthly_income
                FROM Dim_Employee de
                JOIN Dim_Department dd ON de.department_name = dd.department_name
                WHERE de.employee_id = :emp_id 
                  AND :review_date BETWEEN de.effective_start_date AND de.effective_end_date
                LIMIT 1;
            """
            self.execute_statement(
                dw_sql,
                {
                    "review_id": review.review_id,
                    "date_key": date_key,
                    "rating": review.performance_rating,
                    "wlb": review.work_life_balance,
                    "satisfaction": review.job_satisfaction,
                    "training": review.training_times_last_year,
                    "emp_id": review.employee_id,
                    "review_date": str(review.review_date),
                },
                use_dw=True
            )
        except Exception as e:
            self.logger.warning("Could not sync review to Fact_PerformanceReviews: %s", e)

    def get_review_by_id(self, review_id: int) -> Optional[Review]:
        """Fetches a review by primary key."""
        sql = "SELECT * FROM performance_reviews WHERE review_id = :rev_id;"
        rows = self.execute_query(sql, {"rev_id": review_id})
        if not rows:
            return None
        return Review.from_dict(rows[0])

    def get_reviews_by_employee(self, employee_id: int) -> List[Review]:
        """Fetches all performance review cycles for an employee ordered chronologically."""
        sql = """
            SELECT * FROM performance_reviews
            WHERE employee_id = :emp_id
            ORDER BY review_date DESC;
        """
        rows = self.execute_query(sql, {"emp_id": employee_id})
        return [Review.from_dict(r) for r in rows]

    def get_recent_reviews(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent reviews joined with employee metadata for reporting."""
        sql = """
            SELECT 
                r.review_id,
                r.employee_id,
                CONCAT(e.first_name, ' ', e.last_name) AS employee_name,
                e.employee_number,
                d.department_name,
                r.review_date,
                r.review_cycle,
                r.performance_rating,
                r.work_life_balance,
                r.job_satisfaction,
                r.training_times_last_year,
                r.reviewer_comments
            FROM performance_reviews r
            JOIN employees e ON r.employee_id = e.employee_id
            JOIN departments d ON e.department_id = d.department_id
            ORDER BY r.review_date DESC, r.review_id DESC
            LIMIT :limit;
        """
        return self.execute_query(sql, {"limit": limit})

    def update_review(self, review: Review) -> bool:
        """Updates comments and scores for a review."""
        review.validate()
        sql = """
            UPDATE performance_reviews
            SET performance_rating = :rating,
                work_life_balance = :wlb,
                job_satisfaction = :sat,
                training_times_last_year = :training,
                reviewer_comments = :comments
            WHERE review_id = :review_id;
        """
        params = {
            "rating": review.performance_rating,
            "wlb": review.work_life_balance,
            "sat": review.job_satisfaction,
            "training": review.training_times_last_year,
            "comments": review.reviewer_comments,
            "review_id": review.review_id,
        }
        affected = self.execute_statement(sql, params)
        return affected > 0

    def delete_review(self, review_id: int) -> bool:
        """Deletes a review."""
        sql = "DELETE FROM performance_reviews WHERE review_id = :rev_id;"
        affected = self.execute_statement(sql, {"rev_id": review_id})
        return affected > 0
