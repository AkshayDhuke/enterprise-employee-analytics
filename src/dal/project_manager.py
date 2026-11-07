"""
Project Manager Class (Data Access Layer)
Handles project CRUD operations, team member allocations, and workload tracking.
"""

from datetime import date
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.dal.base_manager import BaseManager
from src.entities.project import Project


class ProjectManager(BaseManager):
    """
    Manages persistence for enterprise projects and project assignments.
    Synchronizes project dimension and workload allocations with the Data Warehouse.
    """

    def create_project(self, project: Project) -> int:
        """
        Creates a new project in enterprise_oltp.projects.
        Generates unique project_code if not provided.
        """
        project.validate()

        if not project.project_code:
            max_id = self.execute_scalar("SELECT MAX(project_id) FROM projects;") or 0
            dept_code = f"PRJ-{project.department_id:02d}-{max_id + 1:04d}"
            project.project_code = dept_code

        insert_sql = """
            INSERT INTO projects (
                project_code, project_name, department_id, priority,
                status, start_date, end_date, budget
            ) VALUES (
                :project_code, :project_name, :department_id, :priority,
                :status, :start_date, :end_date, :budget
            );
        """
        params = {
            "project_code": project.project_code,
            "project_name": project.project_name,
            "department_id": project.department_id,
            "priority": project.priority,
            "status": project.status,
            "start_date": str(project.start_date),
            "end_date": str(project.end_date) if project.end_date else None,
            "budget": project.budget,
        }

        try:
            with self.get_oltp_connection() as conn:
                result = conn.execute(text(insert_sql), params)
                project_id = result.lastrowid
                project.project_id = project_id
                self.logger.info("Created Project #%s: %s [%s]", project_id, project.project_name, project.project_code)

                # Sync to Dim_Project in DW
                self._sync_project_to_dw(project)
                return project_id
        except SQLAlchemyError as err:
            self.logger.error("Failed to insert project %s: %s", project.project_name, err)
            raise RuntimeError(f"Database error creating project: {err}") from err

    def _sync_project_to_dw(self, project: Project):
        """Synchronizes project metadata into enterprise_dw.Dim_Project."""
        try:
            dw_insert = """
                INSERT INTO Dim_Project (project_id, project_code, project_name, priority, status, budget)
                VALUES (:project_id, :project_code, :project_name, :priority, :status, :budget)
                ON DUPLICATE KEY UPDATE
                    project_name = VALUES(project_name),
                    priority = VALUES(priority),
                    status = VALUES(status),
                    budget = VALUES(budget);
            """
            dw_params = {
                "project_id": project.project_id,
                "project_code": project.project_code,
                "project_name": project.project_name,
                "priority": project.priority,
                "status": project.status,
                "budget": project.budget,
            }
            self.execute_statement(dw_insert, dw_params, use_dw=True)
        except Exception as e:
            self.logger.warning("Could not sync project to Dim_Project: %s", e)

    def get_project_by_id(self, project_id: int) -> Optional[Project]:
        """Retrieves a project by its primary key ID."""
        sql = "SELECT * FROM projects WHERE project_id = :proj_id;"
        rows = self.execute_query(sql, {"proj_id": project_id})
        if not rows:
            return None
        return Project.from_dict(rows[0])

    def get_all_projects(
        self,
        department_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Project]:
        """Fetches all projects with optional department and status filtering."""
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {}

        if department_id:
            where_clauses.append("department_id = :dept_id")
            params["dept_id"] = department_id
        if status:
            where_clauses.append("status = :status")
            params["status"] = status

        sql = f"""
            SELECT * FROM projects 
            WHERE {' AND '.join(where_clauses)}
            ORDER BY project_id DESC;
        """
        rows = self.execute_query(sql, params)
        return [Project.from_dict(r) for r in rows]

    def update_project(self, project: Project) -> bool:
        """Updates project details and synchronizes status with the Data Warehouse."""
        project.validate()
        sql = """
            UPDATE projects
            SET project_name = :project_name,
                department_id = :department_id,
                priority = :priority,
                status = :status,
                start_date = :start_date,
                end_date = :end_date,
                budget = :budget
            WHERE project_id = :project_id;
        """
        params = {
            "project_name": project.project_name,
            "department_id": project.department_id,
            "priority": project.priority,
            "status": project.status,
            "start_date": str(project.start_date),
            "end_date": str(project.end_date) if project.end_date else None,
            "budget": project.budget,
            "project_id": project.project_id,
        }
        affected = self.execute_statement(sql, params)
        if affected > 0:
            self._sync_project_to_dw(project)
        return affected > 0

    def assign_employee_to_project(
        self,
        employee_id: int,
        project_id: int,
        assigned_role: str,
        allocation_pct: int,
        assigned_date: Optional[date] = None,
    ) -> int:
        """
        Assigns an employee to a project with specified allocation percentage.
        Records entry in OLTP project_assignments and syncs to DW Fact_ProjectAllocations.
        """
        if not (1 <= allocation_pct <= 100):
            raise ValueError("Allocation percentage must be between 1% and 100%.")

        asgn_date = assigned_date or date.today()
        insert_sql = """
            INSERT INTO project_assignments (
                employee_id, project_id, assigned_role, allocation_pct, assigned_date
            ) VALUES (
                :employee_id, :project_id, :assigned_role, :allocation_pct, :assigned_date
            );
        """
        params = {
            "employee_id": employee_id,
            "project_id": project_id,
            "assigned_role": assigned_role,
            "allocation_pct": allocation_pct,
            "assigned_date": str(asgn_date),
        }

        try:
            with self.get_oltp_connection() as conn:
                res = conn.execute(text(insert_sql), params)
                assignment_id = res.lastrowid

            # Trigger fact table loader in DW
            self._sync_allocation_to_dw(assignment_id, employee_id, project_id, asgn_date, allocation_pct, assigned_role)
            return assignment_id
        except SQLAlchemyError as err:
            self.logger.error("Failed to assign employee #%s to project #%s: %s", employee_id, project_id, err)
            raise RuntimeError(f"Project assignment failed: {err}") from err

    def _sync_allocation_to_dw(
        self,
        assignment_id: int,
        employee_id: int,
        project_id: int,
        asgn_date: date,
        allocation_pct: int,
        assigned_role: str
    ):
        """Loads record into Fact_ProjectAllocations using current Dim_Employee SK."""
        try:
            date_key = asgn_date.year * 10000 + asgn_date.month * 100 + asgn_date.day
            dw_sql = """
                INSERT INTO Fact_ProjectAllocations (
                    assignment_id, employee_sk, project_sk, assigned_date_key, allocation_pct, assigned_role
                )
                SELECT 
                    :asgn_id,
                    de.employee_sk,
                    dp.project_sk,
                    :date_key,
                    :alloc_pct,
                    :role
                FROM Dim_Employee de
                JOIN Dim_Project dp ON dp.project_id = :proj_id
                WHERE de.employee_id = :emp_id AND de.is_current = 1
                LIMIT 1;
            """
            self.execute_statement(
                dw_sql,
                {
                    "asgn_id": assignment_id,
                    "date_key": date_key,
                    "alloc_pct": allocation_pct,
                    "role": assigned_role,
                    "proj_id": project_id,
                    "emp_id": employee_id,
                },
                use_dw=True
            )
        except Exception as e:
            self.logger.warning("Could not sync project allocation to Fact table: %s", e)

    def release_employee_from_project(self, assignment_id: int, released_date: Optional[date] = None) -> bool:
        """Marks an assignment as released."""
        rel_date = released_date or date.today()
        sql = "UPDATE project_assignments SET released_date = :rel_date WHERE assignment_id = :asgn_id;"
        affected = self.execute_statement(sql, {"rel_date": str(rel_date), "asgn_id": assignment_id})
        return affected > 0

    def get_project_assignments(self, project_id: int) -> List[Dict[str, Any]]:
        """Returns all employees assigned to a given project."""
        sql = """
            SELECT 
                pa.assignment_id,
                pa.employee_id,
                CONCAT(e.first_name, ' ', e.last_name) AS employee_name,
                e.employee_number,
                pa.assigned_role,
                pa.allocation_pct,
                pa.assigned_date,
                pa.released_date
            FROM project_assignments pa
            JOIN employees e ON pa.employee_id = e.employee_id
            WHERE pa.project_id = :proj_id
            ORDER BY pa.assigned_date DESC;
        """
        return self.execute_query(sql, {"proj_id": project_id})

    def get_employee_assignments(self, employee_id: int) -> List[Dict[str, Any]]:
        """Returns all projects assigned to an employee with total active workload."""
        sql = """
            SELECT 
                pa.assignment_id,
                p.project_id,
                p.project_code,
                p.project_name,
                p.priority,
                p.status,
                pa.assigned_role,
                pa.allocation_pct,
                pa.assigned_date,
                pa.released_date
            FROM project_assignments pa
            JOIN projects p ON pa.project_id = p.project_id
            WHERE pa.employee_id = :emp_id
            ORDER BY pa.assigned_date DESC;
        """
        return self.execute_query(sql, {"emp_id": employee_id})

    def delete_project(self, project_id: int) -> bool:
        """Removes a project and cascades assignments."""
        sql = "DELETE FROM projects WHERE project_id = :proj_id;"
        affected = self.execute_statement(sql, {"proj_id": project_id})
        return affected > 0
