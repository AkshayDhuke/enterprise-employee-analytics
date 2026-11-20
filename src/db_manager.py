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

            def _get_val(key: str, default: str) -> str:
                # 1. Check direct environment variables (case-insensitive)
                for env_k in (key, key.lower(), key.upper()):
                    val = os.getenv(env_k)
                    if val:
                        return val
                # 2. Check Streamlit Cloud secrets (top-level and nested sections)
                try:
                    import streamlit as st
                    if hasattr(st, "secrets"):
                        # Top-level check (case-insensitive)
                        for sec_k, sec_v in st.secrets.items():
                            if sec_k.lower() == key.lower():
                                return str(sec_v)
                        # Nested sections check (e.g. [tidb], [mysql], [database], [connections])
                        for sec_name in ["tidb", "mysql", "database", "connections", "tidbcloud"]:
                            if sec_name in st.secrets and hasattr(st.secrets[sec_name], "items"):
                                for sub_k, sub_v in st.secrets[sec_name].items():
                                    short_k = key.lower().replace("db_", "")
                                    if sub_k.lower() in (key.lower(), short_k):
                                        return str(sub_v)
                except Exception:
                    pass
                return default

            # Auto-detect Streamlit Cloud environment or headless containers
            is_cloud = os.path.exists("/mount/src") or "STREAMLIT" in os.environ.get("HOSTNAME", "")

            default_user = "3W1Y2fU7xQME74Y.root" if is_cloud else "root"
            default_pwd = "h9U454ewoOyWb4MH" if is_cloud else "root@2003"
            default_host = "gateway01.ap-northeast-1.prod.aws.tidbcloud.com" if is_cloud else "127.0.0.1"
            default_port = "4000" if is_cloud else "3306"

            self.user = user or _get_val("DB_USER", default_user)
            self.password = password or _get_val("DB_PASSWORD", default_pwd)
            self.host = host or _get_val("DB_HOST", default_host)
            self.port = port or _get_val("DB_PORT", default_port)
            self.oltp_db = oltp_db or _get_val("OLTP_DB_NAME", "enterprise_oltp")
            self.dw_db = dw_db or _get_val("DW_DB_NAME", "enterprise_dw")

            encoded_pwd = urllib.parse.quote_plus(self.password)
            # Connection URLs
            self._oltp_url = f"mysql+pymysql://{self.user}:{encoded_pwd}@{self.host}:{self.port}/{self.oltp_db}"
            self._dw_url = f"mysql+pymysql://{self.user}:{encoded_pwd}@{self.host}:{self.port}/{self.dw_db}"
            self._pool_size = pool_size
            self._max_overflow = max_overflow

            # Lazy engines
            self._oltp_engine: Engine = None
            self._dw_engine: Engine = None

            # SSL connect args for cloud databases (e.g. TiDB Cloud)
            self._connect_args = {}
            ssl_val = _get_val("DB_SSL", "false")
            if ssl_val.lower() in ("true", "1") or "tidbcloud.com" in self.host.lower():
                self._connect_args["ssl"] = {}

            self._initialized = True

    @property
    def oltp_engine(self) -> Engine:
        """Returns the SQLAlchemy Engine for the OLTP database (lazy-loaded)."""
        if self._oltp_engine is None:
            with self._lock:
                if self._oltp_engine is None:
                    self._oltp_engine = create_engine(
                        self._oltp_url,
                        connect_args=self._connect_args,
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
                        connect_args=self._connect_args,
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
        DatabaseConnection._instances.clear()
        self._initialized = False
