"""
Root-level db_manager alias for compatibility and direct execution.
Re-exports DatabaseConnection from src.db_manager.
"""

from src.db_manager import DatabaseConnection

__all__ = ["DatabaseConnection"]
