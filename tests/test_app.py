from time import sleep, time
from fastapi.testclient import TestClient
import pytest
from tests.app import app, fake_db, rate_limit_store, cache_storage, error_log

client = TestClient(app)


def test_read_items() -> None:
    response = client.get("/items/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 2


def test_create_item() -> None:
    response = client.post("/items/", json={"name": "NewItem"})
    assert response.status_code == 200
    assert response.headers.get("X-Custom-Header") == "CustomValue"
    data = response.json()
    assert data["message"] == "Item created"
    assert data["item"]["name"] == "NewItem"


def test_read_current_user_unauthorized() -> None:
    response = client.get("/users/me")
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Unauthorized"


def test_read_current_user_authorized() -> None:
    headers = {"token": "valid_token"}
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user"] == "user_from_token"


@pytest.mark.parametrize(
    "url",
    [
        "/header-test-v1/",
        "/header-test-v2/",
    ],
)
def test_generate_report(url: str) -> None:
    response = client.get(url)
    assert response.status_code == 200
    assert response.headers.get("X-Custom-Header") == "CustomValue"
    data = response.json()
    assert data["report"] == "This is your report"


def test_update_user_success() -> None:
    user_id = 1
    new_data = {"name": "John Updated", "email": "john_updated@example.com"}
    response = client.put(f"/users/{user_id}", json=new_data)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == f"User {user_id} updated"
    assert data["user"]["name"] == new_data["name"]
    assert data["user"]["email"] == new_data["email"]


def test_update_user_not_found() -> None:
    user_id = 999
    new_data = {"name": "Ghost User", "email": "ghost@example.com"}
    response = client.put(f"/users/{user_id}", json=new_data)
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "User not found"


def test_delete_user_unauthorized() -> None:
    user_id = 2
    response = client.delete(f"/users/{user_id}")
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Unauthorized"


def test_delete_user_success() -> None:
    user_id = 2
    headers = {"token": "valid_token"}
    response = client.delete(f"/users/{user_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == f"User {user_id} deleted"
    assert user_id not in fake_db["users"]


def test_delete_user_not_found() -> None:
    user_id = 999
    headers = {"token": "valid_token"}
    response = client.delete(f"/users/{user_id}", headers=headers)
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "User not found"


def test_rate_limiting() -> None:
    rate_limit_store.clear()

    for _ in range(5):
        response = client.get("/limited-endpoint")
        assert response.status_code == 200

    # Sixth request should be rate-limited
    response = client.get("/limited-endpoint")
    assert response.status_code == 429
    assert response.json()["detail"] == "Too Many Requests"

    # Wait for rate limit period to expire
    sleep(1)

    response = client.get("/limited-endpoint")
    assert response.status_code == 200


def test_cached_response() -> None:
    cache_storage.clear()
    first_time = time()
    data1 = client.get("/expensive-operation").json()
    second_time = time()
    data2 = client.get("/expensive-operation").json()
    end_time = time()

    assert second_time - first_time >= 1  # The endpoint takes 1 second when not cached
    assert end_time - second_time < 0.1  # Should be near-instantaneous when cached
    assert data1 == data2

    # Wait for the cache to expire
    sleep(1)

    data3 = client.get("/expensive-operation").json()
    assert data1 != data3


def test_error_handling_success() -> None:
    response = client.get("/may-fail?should_fail=false")
    assert response.status_code == 200
    assert response.json()["message"] == "Operation succeeded"


def test_error_handling_failure() -> None:
    error_log.clear()

    response = client.get("/may-fail?should_fail=true")
    assert response.status_code == 500
    assert len(error_log) == 1

    # Check that error was logged
    assert len(error_log) == 1
    assert error_log[0]["function"] == "may_fail_operation"


def test_error_log_endpoint() -> None:
    response = client.get("/error-log")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_expects_header() -> None:
    headers = {"requestor_id": "potato@me"}
    response = client.get("/headers", headers=headers)
    assert response.status_code == 200
    assert response.json() == headers
