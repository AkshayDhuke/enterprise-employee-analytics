"""Database-backed authentication and role checks for the Streamlit app."""

import base64
import hashlib
import hmac
import os
import secrets
from typing import Any, Dict, Optional

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
from sqlalchemy import text

from src.db_manager import DatabaseConnection


_HASH_ITERATIONS = 600_000
_HASH_ALGORITHM = "sha256"


def require_hr(role: str) -> None:
    """Reject write operations unless the authenticated user has the HR role."""
    if role != "hr":
        raise PermissionError("Only HR users may add or update records.")


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(_HASH_ALGORITHM, password.encode("utf-8"), salt, _HASH_ITERATIONS)
    return "$".join((
        "pbkdf2",
        _HASH_ALGORITHM,
        str(_HASH_ITERATIONS),
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    ))


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, algorithm, iterations, encoded_salt, encoded_digest = stored_hash.split("$")
        if scheme != "pbkdf2" or algorithm != _HASH_ALGORITHM:
            return False
        iteration_count = int(iterations)
        if iteration_count != _HASH_ITERATIONS:
            return False
        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected_digest = base64.urlsafe_b64decode(encoded_digest.encode("ascii"))
        actual_digest = hashlib.pbkdf2_hmac(
            algorithm, password.encode("utf-8"), salt, iteration_count
        )
        return hmac.compare_digest(actual_digest, expected_digest)
    except (ValueError, TypeError):
        return False


class AuthenticationManager:
    """Stores application accounts in enterprise_oltp and verifies credentials."""

    def __init__(self, db: Optional[DatabaseConnection] = None):
        self.db = db or DatabaseConnection()
        self._ensure_users_table()

    def _ensure_users_table(self) -> None:
        with self.db.get_oltp_connection() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS app_users (
                    user_id INT AUTO_INCREMENT PRIMARY KEY,
                    full_name VARCHAR(150) NOT NULL,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    role ENUM('hr', 'viewer') NOT NULL DEFAULT 'viewer',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
            """))

    @staticmethod
    def _user_from_row(row: Any) -> Dict[str, Any]:
        return {
            "user_id": row["user_id"],
            "full_name": row["full_name"],
            "email": row["email"],
            "role": row["role"],
        }

    def register(
        self,
        full_name: str,
        email: str,
        password: str,
        hr_signup_code: str = "",
    ) -> Dict[str, Any]:
        full_name = full_name.strip()
        email = email.strip().lower()
        configured_code = os.getenv("HR_SIGNUP_CODE", "")
        if not configured_code:
            try:
                configured_code = str(st.secrets["HR_SIGNUP_CODE"])
            except (KeyError, StreamlitSecretNotFoundError):
                configured_code = ""

        if (
            not full_name
            or len(full_name) > 150
            or not email
            or len(email) > 255
            or len(password) < 12
            or len(password) > 1024
        ):
            raise ValueError(
                "Enter a name and email, and use a password between 12 and 1024 characters."
            )

        role = "viewer"
        if hr_signup_code:
            if not configured_code:
                raise ValueError("HR signup is not configured. Contact the system administrator.")
            if not hmac.compare_digest(hr_signup_code, configured_code):
                raise ValueError("The HR signup code is invalid.")
            role = "hr"

        with self.db.get_oltp_connection() as conn:
            existing = conn.execute(
                text("SELECT user_id FROM app_users WHERE email = :email"),
                {"email": email},
            ).first()
            if existing:
                raise ValueError("An account with this email already exists.")

            result = conn.execute(
                text("""
                    INSERT INTO app_users (full_name, email, password_hash, role)
                    VALUES (:full_name, :email, :password_hash, :role)
                """),
                {
                    "full_name": full_name,
                    "email": email,
                    "password_hash": _hash_password(password),
                    "role": role,
                },
            )
            user_id = result.lastrowid

        return {
            "user_id": user_id,
            "full_name": full_name,
            "email": email,
            "role": role,
        }

    def login(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        with self.db.get_oltp_connection() as conn:
            row = conn.execute(
                text("""
                    SELECT user_id, full_name, email, role, password_hash
                    FROM app_users
                    WHERE email = :email
                """),
                {"email": email.strip().lower()},
            ).mappings().first()

        if not row or not _verify_password(password, row["password_hash"]):
            return None
        return self._user_from_row(row)
