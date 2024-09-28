import unittest
from fastapi.testclient import TestClient
from fastapi import status
import logging

from app import app

class TestFastAPIIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Set up logging to capture logs for testing
        logging.basicConfig(level=logging.INFO)
        cls.logger = logging.getLogger("app")

    def setUp(self):
        self.client = TestClient(app)
        self.valid_user_token = "alice"  # Regular user
        self.admin_user_token = "bob"    # Admin user

    def test_plain_public_endpoint(self):
        response = self.client.get("/public")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"message": "This is a public endpoint"})

    def test_plain_read_current_user_authenticated(self):
        headers = {"X-Auth-Token": self.valid_user_token}
        response = self.client.get("/plain/users/me", headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {"user": {"username": "alice", "roles": ["user"]}},
        )

    def test_plain_read_current_user_unauthenticated(self):
        response = self.client.get("/plain/users/me")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json(), {"detail": "Unauthorized"})

    def test_plain_admin_endpoint_as_admin(self):
        headers = {"X-Auth-Token": self.admin_user_token}
        response = self.client.get("/plain/admin", headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"message": "This is admin data"})

    def test_plain_admin_endpoint_as_user(self):
        headers = {"X-Auth-Token": self.valid_user_token}
        response = self.client.get("/plain/admin", headers=headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json(), {"detail": "Forbidden: Admins only"})

    def test_plain_admin_endpoint_unauthenticated(self):
        response = self.client.get("/plain/admin")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json(), {"detail": "Unauthorized"})

    def test_plain_error_endpoint_logging(self):
        headers = {"X-Auth-Token": self.valid_user_token}
        with self.assertLogs("app", level="INFO") as cm:
            response = self.client.get("/plain/error", headers=headers)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.json(), {"detail": "Internal Server Error"})
        # Verify that the log contains the expected message
        self.assertIn("User alice made a request", cm.output[0])

    def test_plain_logging_in_admin_endpoint(self):
        headers = {"X-Auth-Token": self.admin_user_token}
        with self.assertLogs("app", level="INFO") as cm:
            response = self.client.get("/plain/admin", headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("User bob made a request", cm.output[0])

    def test_plain_unauthorized_access_logging(self):
        headers = {"X-Auth-Token": "invalid_user"}
        # No INFO log should be generated because the user is not authenticated
        with self.assertRaises(AssertionError):
            with self.assertLogs("app", level="INFO"):
                response = self.client.get("/plain/admin", headers=headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_decorated_read_current_user_authenticated(self):
        headers = {"X-Auth-Token": self.valid_user_token}
        response = self.client.get("/decorated/users/me", headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {"user": {"username": "alice", "roles": ["user"]}},
        )

    def test_decorated_read_current_user_unauthenticated(self):
        response = self.client.get("/decorated/users/me")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json(), {"detail": "Unauthorized"})

    def test_decorated_admin_endpoint_as_admin(self):
        headers = {"X-Auth-Token": self.admin_user_token}
        response = self.client.get("/decorated/admin", headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"message": "This is admin data"})

    def test_decorated_admin_endpoint_as_user(self):
        headers = {"X-Auth-Token": self.valid_user_token}
        response = self.client.get("/decorated/admin", headers=headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json(), {"detail": "Forbidden: Admins only"})

    def test_decorated_admin_endpoint_unauthenticated(self):
        response = self.client.get("/decorated/admin")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json(), {"detail": "Unauthorized"})

    def test_decorated_error_endpoint_logging(self):
        headers = {"X-Auth-Token": self.valid_user_token}
        with self.assertLogs("app", level="INFO") as cm:
            response = self.client.get("/decorated/error", headers=headers)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.json(), {"detail": "Internal Server Error"})
        # Verify that the log contains the expected message
        self.assertIn("User alice made a request", cm.output[0])

    def test_decorated_logging_in_admin_endpoint(self):
        headers = {"X-Auth-Token": self.admin_user_token}
        with self.assertLogs("app", level="INFO") as cm:
            response = self.client.get("/decorated/admin", headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("User bob made a request", cm.output[0])

    def test_decorated_unauthorized_access_logging(self):
        headers = {"X-Auth-Token": "invalid_user"}
        # No INFO log should be generated because the user is not authenticated
        with self.assertRaises(AssertionError):
            with self.assertLogs("app", level="INFO"):
                response = self.client.get("/decorated/admin", headers=headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

if __name__ == "__main__":
    unittest.main()
