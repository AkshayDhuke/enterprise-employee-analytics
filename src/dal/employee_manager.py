"""
Employee Manager Class (Data Access Layer)
Handles CRUD operations for employees in OLTP and triggers SCD Type 2 updates in the Data Warehouse.
"""

from datetime import date
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.dal.base_manager import BaseManager
from src.entities.employee import Employee


class EmployeeManager(BaseManager):
    """
    Manages persistence, retrieval, and SCD Type 2 lifecycle updates for Employees.
    Inherits from BaseManager for unified connection pooling and exception handling.
    """

    def create_employee(self, employee: Employee) -> int:
        """
        Creates a new employee record in enterprise_oltp.employees.
        Returns the generated employee_id.
        """
        employee.validate()

        # Generate unique employee_number if not already set
        if not employee.employee_number:
            max_num_query = "SELECT MAX(employee_id) FROM employees;"
            max_id = self.execute_scalar(max_num_query) or 0
            employee.employee_number = f"EMP-{max_id + 1:05d}"

        insert_sql = """
            INSERT INTO employees (
                employee_number, first_name, last_name, email, gender, age,
                department_id, job_role, job_level, monthly_income, education_field,
                years_at_company, attrition, hire_date
            ) VALUES (
                :employee_number, :first_name, :last_name, :email, :gender, :age,
                :department_id, :job_role, :job_level, :monthly_income, :education_field,
                :years_at_company, :attrition, :hire_date
            );
        """
        params = {
            "employee_number": employee.employee_number,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "email": employee.email,
            "gender": employee.gender,
            "age": employee.age,
            "department_id": employee.department_id,
            "job_role": employee.job_role,
            "job_level": employee.job_level,
            "monthly_income": employee.monthly_income,
            "education_field": employee.education_field,
            "years_at_company": employee.years_at_company,
            "attrition": employee.attrition,
            "hire_date": str(employee.hire_date),
        }

        try:
            with self.get_oltp_connection() as conn:
                result = conn.execute(text(insert_sql), params)
                emp_id = result.lastrowid
                employee.employee_id = emp_id
                self.logger.info("Successfully created Employee #%s (%s)", emp_id, employee.full_name)

                # Initialize matching Dim_Employee record in DW
                self._sync_new_employee_to_dw(employee)
                return emp_id
        except SQLAlchemyError as err:
            self.logger.error("Failed to insert employee %s: %s", employee.full_name, err)
            raise RuntimeError(f"Database error while creating employee: {err}") from err

    def _sync_new_employee_to_dw(self, employee: Employee):
        """Initializes a baseline Dim_Employee version 1 record in enterprise_dw."""
        try:
            dept_query = "SELECT department_name FROM departments WHERE department_id = :dept_id;"
            dept_name = self.execute_scalar(dept_query, {"dept_id": employee.department_id}) or "General"

            dw_insert = """
                INSERT INTO Dim_Employee (
                    employee_id, employee_number, full_name, gender, age,
                    department_name, job_role, job_level, monthly_income,
                    education_field, years_at_company, attrition, hire_date,
                    effective_start_date, effective_end_date, is_current, version
                ) VALUES (
                    :employee_id, :employee_number, :full_name, :gender, :age,
                    :department_name, :job_role, :job_level, :monthly_income,
                    :education_field, :years_at_company, :attrition, :hire_date,
                    :effective_start_date, '9999-12-31', 1, 1
                );
            """
            dw_params = {
                "employee_id": employee.employee_id,
                "employee_number": employee.employee_number,
                "full_name": employee.full_name,
                "gender": employee.gender,
                "age": employee.age,
                "department_name": dept_name,
                "job_role": employee.job_role,
                "job_level": employee.job_level,
                "monthly_income": employee.monthly_income,
                "education_field": employee.education_field,
                "years_at_company": employee.years_at_company,
                "attrition": employee.attrition,
                "hire_date": str(employee.hire_date),
                "effective_start_date": str(employee.hire_date),
            }
            self.execute_statement(dw_insert, dw_params, use_dw=True)
        except Exception as e:
            self.logger.warning("Could not immediately sync new employee to DW: %s", e)

    def get_employee_by_id(self, employee_id: int) -> Optional[Employee]:
        """Fetches an active employee by ID."""
        sql = "SELECT * FROM employees WHERE employee_id = :emp_id;"
        rows = self.execute_query(sql, {"emp_id": employee_id})
        if not rows:
            return None
        return Employee.from_dict(rows[0])

    def get_employee_by_number(self, employee_number: str) -> Optional[Employee]:
        """Fetches an employee by their unique business employee_number."""
        sql = "SELECT * FROM employees WHERE employee_number = :emp_num;"
        rows = self.execute_query(sql, {"emp_num": employee_number})
        if not rows:
            return None
        return Employee.from_dict(rows[0])

    def get_all_employees(
        self,
        limit: int = 100,
        offset: int = 0,
        department_id: Optional[int] = None,
        attrition: Optional[str] = None
    ) -> List[Employee]:
        """Retrieves paginated employee records with optional filtering."""
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {"limit": limit, "offset": offset}

        if department_id:
            where_clauses.append("department_id = :dept_id")
            params["dept_id"] = department_id
        if attrition:
            where_clauses.append("attrition = :attrition")
            params["attrition"] = attrition

        sql = f"""
            SELECT * FROM employees 
            WHERE {' AND '.join(where_clauses)}
            ORDER BY employee_id DESC
            LIMIT :limit OFFSET :offset;
        """
        rows = self.execute_query(sql, params)
        return [Employee.from_dict(r) for r in rows]

    def search_employees(self, search_term: str, limit: int = 50) -> List[Employee]:
        """Searches employees by name, email, employee_number, or job role."""
        sql = """
            SELECT * FROM employees
            WHERE first_name LIKE :term 
               OR last_name LIKE :term 
               OR email LIKE :term 
               OR employee_number LIKE :term 
               OR job_role LIKE :term
            ORDER BY employee_id DESC
            LIMIT :limit;
        """
        rows = self.execute_query(sql, {"term": f"%{search_term}%", "limit": limit})
        return [Employee.from_dict(r) for r in rows]

    def update_employee(self, employee: Employee) -> bool:
        """Updates standard employee demographic profile attributes in OLTP."""
        employee.validate()
        sql = """
            UPDATE employees
            SET first_name = :first_name,
                last_name = :last_name,
                email = :email,
                gender = :gender,
                age = :age,
                education_field = :education_field,
                years_at_company = :years_at_company
            WHERE employee_id = :employee_id;
        """
        params = {
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "email": employee.email,
            "gender": employee.gender,
            "age": employee.age,
            "education_field": employee.education_field,
            "years_at_company": employee.years_at_company,
            "employee_id": employee.employee_id,
        }
        affected = self.execute_statement(sql, params)
        return affected > 0

    def update_employee_scd2(
        self,
        employee_id: int,
        new_department_id: int,
        new_job_role: str,
        new_job_level: int,
        new_salary: float,
        attrition: str = "No",
        effective_date: Optional[date] = None,
    ) -> bool:
        """
        Triggers an SCD Type 2 update in the Data Warehouse by invoking the stored procedure:
        CALL enterprise_dw.sp_update_employee_scd2(...)
        Expires previous version and inserts a new point-in-time version in Dim_Employee.
        Synchronizes OLTP automatically.
        """
        eff_date = effective_date or date.today()

        call_proc_sql = """
            CALL sp_update_employee_scd2(
                :p_employee_id,
                :p_new_department_id,
                :p_new_job_role,
                :p_new_job_level,
                :p_new_salary,
                :p_attrition,
                :p_effective_date
            );
        """
        params = {
            "p_employee_id": employee_id,
            "p_new_department_id": new_department_id,
            "p_new_job_role": new_job_role,
            "p_new_job_level": new_job_level,
            "p_new_salary": new_salary,
            "p_attrition": attrition,
            "p_effective_date": str(eff_date),
        }

        try:
            with self.get_dw_connection() as conn:
                conn.execute(text(call_proc_sql), params)
            self.logger.info(
                "SCD Type 2 procedure executed for Emp #%s: Dept=%s, Role=%s, Salary=$%s",
                employee_id, new_department_id, new_job_role, new_salary
            )
            return True
        except SQLAlchemyError as err:
            self.logger.error("Failed to execute SCD2 procedure for emp #%s: %s", employee_id, err)
            raise RuntimeError(f"SCD Type 2 update procedure failed: {err}") from err

    def delete_employee(self, employee_id: int, soft_delete: bool = True) -> bool:
        """
        Deletes or soft-deletes (sets attrition='Yes') an employee record.
        """
        if soft_delete:
            sql = "UPDATE employees SET attrition = 'Yes' WHERE employee_id = :emp_id;"
            affected = self.execute_statement(sql, {"emp_id": employee_id})
            return affected > 0
        else:
            sql = "DELETE FROM employees WHERE employee_id = :emp_id;"
            affected = self.execute_statement(sql, {"emp_id": employee_id})
            return affected > 0

    def get_departments(self) -> List[Dict[str, Any]]:
        """Returns all registered corporate departments."""
        sql = "SELECT department_id, department_name, cost_center_code, location FROM departments ORDER BY department_id ASC;"
        return self.execute_query(sql)
