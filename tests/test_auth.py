"""Authentication and write authorization tests."""

from contextlib import contextmanager
import unittest
from unittest.mock import patch

from app.auth import AuthenticationManager, _hash_password, _verify_password, require_hr
from app.data_provider import DataProvider


class FakeResult:
    lastrowid = 7

    def first(self):
        return None


class FakeConnection:
    def __init__(self):
        self.inserted_user = None

    def execute(self, statement, params=None):
        if str(statement).lstrip().startswith("INSERT"):
            self.inserted_user = params
        return FakeResult()


class FakeDatabase:
    def __init__(self):
        self.connection = FakeConnection()

    @contextmanager
    def get_oltp_connection(self):
        yield self.connection


class TestPasswordHashing(unittest.TestCase):
    def test_password_hash_verifies_without_storing_plaintext(self):
        password = "correct horse battery staple"
        stored_hash = _hash_password(password)

        self.assertNotIn(password, stored_hash)
        self.assertTrue(_verify_password(password, stored_hash))
        self.assertFalse(_verify_password("incorrect password", stored_hash))

    def test_malformed_hash_is_rejected(self):
        self.assertFalse(_verify_password("password", "not-a-valid-hash"))


class TestAccountRegistration(unittest.TestCase):
    def setUp(self):
        self.auth = object.__new__(AuthenticationManager)
        self.auth.db = FakeDatabase()

    @patch.dict("os.environ", {"HR_SIGNUP_CODE": "private-invitation"})
    def test_signup_assigns_viewer_by_default_and_hr_only_with_code(self):
        viewer = self.auth.register(
            "Read Only", "VIEWER@example.com", "a long enough password"
        )
        hr_user = self.auth.register(
            "HR User",
            "hr@example.com",
            "another long password",
            hr_signup_code="private-invitation",
        )

        self.assertEqual(viewer["role"], "viewer")
        self.assertEqual(viewer["email"], "viewer@example.com")
        self.assertEqual(hr_user["role"], "hr")
        self.assertNotIn("password_hash", hr_user)

    @patch.dict("os.environ", {"HR_SIGNUP_CODE": "private-invitation"})
    def test_invalid_hr_code_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid"):
            self.auth.register(
                "Someone",
                "someone@example.com",
                "a long enough password",
                hr_signup_code="wrong-code",
            )


class TestWriteAuthorization(unittest.TestCase):
    def setUp(self):
        self.provider = object.__new__(DataProvider)

    def test_viewer_cannot_call_any_data_write_operation(self):
        operations = [
            lambda: self.provider.create_employee({}, actor_role="viewer"),
            lambda: self.provider.update_employee_scd2(
                1, 1, "Analyst", 2, 5000, actor_role="viewer"
            ),
            lambda: self.provider.terminate_employee(1, actor_role="viewer"),
            lambda: self.provider.create_project({}, actor_role="viewer"),
            lambda: self.provider.submit_review({}, actor_role="viewer"),
        ]

        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaises(PermissionError):
                    operation()

    def test_hr_can_pass_write_authorization(self):
        require_hr("hr")


if __name__ == "__main__":
    unittest.main()
