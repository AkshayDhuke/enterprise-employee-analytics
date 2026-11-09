"""
Database Connection Manager utilizing the Singleton Design Pattern.
Safely manages database engines and connection pools for both OLTP and Data Warehouse schemas.
"""

import os
import threading
import urllib.parse
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.exc import SQLAlchemyError


class DatabaseConnection:
    """
    Singleton Database Connection Manager.
    Ensures only a single instance manages the MySQL database connection pools
    for enterprise_oltp and enterprise_dw across the entire application lifecycle.
    """
    _instances = {}
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super(DatabaseConnection, cls).__new__(cls)
                    instance._initialized = False
                    cls._instances[cls] = instance
        return cls._instances[cls]

    def __init__(
        self,
        user: str = None,
        password: str = None,
        host: str = None,
        port: str = None,
        oltp_db: str = "enterprise_oltp",
        dw_db: str = "enterprise_dw",
        pool_size: int = 5,
        max_overflow: int = 10,
    ):
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            self.user = user or os.getenv("DB_USER", "root")
            self.password = password or os.getenv("DB_PASSWORD", "root@2003")
            self.host = host or os.getenv("DB_HOST", "127.0.0.1")
            self.port = port or os.getenv("DB_PORT", "3306")
            self.oltp_db = oltp_db
            self.dw_db = dw_db

            encoded_pwd = urllib.parse.quote_plus(self.password)
            # Connection URLs
            self._oltp_url = f"mysql+pymysql://{self.user}:{encoded_pwd}@{self.host}:{self.port}/{self.oltp_db}"
            self._dw_url = f"mysql+pymysql://{self.user}:{encoded_pwd}@{self.host}:{self.port}/{self.dw_db}"
            self._pool_size = pool_size
            self._max_overflow = max_overflow

            # Lazy engines
            self._oltp_engine: Engine = None
            self._dw_engine: Engine = None

            self._initialized = True

    @property
    def oltp_engine(self) -> Engine:
        """Returns the SQLAlchemy Engine for the OLTP database (lazy-loaded)."""
        if self._oltp_engine is None:
            with self._lock:
                if self._oltp_engine is None:
                    self._oltp_engine = create_engine(
                        self._oltp_url,
                        pool_size=self._pool_size,
                        max_overflow=self._max_overflow,
                        pool_recycle=3600,
                        pool_pre_ping=True
                    )
        return self._oltp_engine

    @property
    def dw_engine(self) -> Engine:
        """Returns the SQLAlchemy Engine for the Data Warehouse (lazy-loaded)."""
        if self._dw_engine is None:
            with self._lock:
                if self._dw_engine is None:
                    self._dw_engine = create_engine(
                        self._dw_url,
                        pool_size=self._pool_size,
                        max_overflow=self._max_overflow,
                        pool_recycle=3600,
                        pool_pre_ping=True
                    )
        return self._dw_engine

    @contextmanager
    def get_oltp_connection(self) -> Generator[Connection, None, None]:
        """Context manager yielding a transactional OLTP database connection."""
        conn = self.oltp_engine.connect()
        trans = conn.begin()
        try:
            yield conn
            trans.commit()
        except Exception as e:
            trans.rollback()
            raise SQLAlchemyError(f"OLTP Transaction failed and was rolled back: {e}") from e
        finally:
            conn.close()

    @contextmanager
    def get_dw_connection(self) -> Generator[Connection, None, None]:
        """Context manager yielding a read/write Data Warehouse database connection."""
        conn = self.dw_engine.connect()
        trans = conn.begin()
        try:
            yield conn
            trans.commit()
        except Exception as e:
            trans.rollback()
            raise SQLAlchemyError(f"DW Transaction failed and was rolled back: {e}") from e
        finally:
            conn.close()

    def test_connections(self) -> dict:
        """Verifies connectivity to both OLTP and DW databases."""
        status = {"oltp": False, "dw": False, "errors": {}}

        try:
            with self.get_oltp_connection() as conn:
                conn.execute(text("SELECT 1;"))
                status["oltp"] = True
        except Exception as e:
            status["errors"]["oltp"] = str(e)

        try:
            with self.get_dw_connection() as conn:
                conn.execute(text("SELECT 1;"))
                status["dw"] = True
        except Exception as e:
            status["errors"]["dw"] = str(e)

        return status

    def close_all(self):
        """Disposes connection pools cleanly."""
        if hasattr(self, "_oltp_engine") and self._oltp_engine:
            self._oltp_engine.dispose()
        if hasattr(self, "_dw_engine") and self._dw_engine:
            self._dw_engine.dispose()
        DatabaseConnection._instance = None
        self._initialized = False
