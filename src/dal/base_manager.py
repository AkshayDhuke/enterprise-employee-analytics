"""
Base Manager Class for Data Access Layer (DAL)
Inherits directly from DatabaseConnection to manage database interactions,
providing standardized transaction wrapping, parameter binding, and robust try-except error handling.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from src.db_manager import DatabaseConnection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class BaseManager(DatabaseConnection):
    """
    Abstract base data access manager inheriting from the Singleton DatabaseConnection.
    Encapsulates core SQL execution patterns with robust try-except error handling.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        use_dw: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Executes a SELECT query and returns rows as dictionaries.
        Safely isolates execution within try-except blocks.
        """
        params = params or {}
        conn_context = self.get_dw_connection() if use_dw else self.get_oltp_connection()

        try:
            with conn_context as conn:
                result = conn.execute(text(query), params)
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result.fetchall()]
        except SQLAlchemyError as err:
            target = "DW" if use_dw else "OLTP"
            self.logger.error("SQL Error in %s execution: %s | Query: %s", target, err, query)
            raise RuntimeError(f"Database query error [{target}]: {err}") from err
        except Exception as ex:
            self.logger.error("Unexpected error during query execution: %s", ex)
            raise

    def execute_scalar(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        use_dw: bool = False
    ) -> Any:
        """Executes a query and returns a single scalar value."""
        params = params or {}
        conn_context = self.get_dw_connection() if use_dw else self.get_oltp_connection()

        try:
            with conn_context as conn:
                result = conn.execute(text(query), params)
                return result.scalar()
        except SQLAlchemyError as err:
            self.logger.error("Error executing scalar query: %s", err)
            raise RuntimeError(f"Database scalar execution error: {err}") from err

    def execute_statement(
        self,
        statement: str,
        params: Optional[Dict[str, Any]] = None,
        use_dw: bool = False
    ) -> int:
        """
        Executes an INSERT, UPDATE, or DELETE statement.
        Returns the rowcount of affected records.
        """
        params = params or {}
        conn_context = self.get_dw_connection() if use_dw else self.get_oltp_connection()

        try:
            with conn_context as conn:
                result = conn.execute(text(statement), params)
                return result.rowcount
        except SQLAlchemyError as err:
            self.logger.error("Database write error: %s | Statement: %s", err, statement)
            raise RuntimeError(f"Database statement execution failed: {err}") from err
