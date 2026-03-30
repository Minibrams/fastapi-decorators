from fastapi import FastAPI, status
from fastapi.testclient import TestClient
import pytest
from tests.app import (
    app,
    cache_storage,
    error_log,
    expensive_operation_stats,
    fake_db,
    rate_limit_store,
)
from fastapi_decorators import depends

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

    # Force rate-limit window expiry
    request_id = next(iter(rate_limit_store))
    rate_limit_store[request_id]["last_reset"] -= 2

    response = client.get("/limited-endpoint")
    assert response.status_code == 200


def test_cached_response() -> None:
    cache_storage.clear()
    expensive_operation_stats["calls"] = 0

    data1 = client.get("/expensive-operation").json()
    assert expensive_operation_stats["calls"] == 1

    data2 = client.get("/expensive-operation").json()

    assert data1 == data2
    assert expensive_operation_stats["calls"] == 1

    # Force cache expiry
    cache_key = "expensive_operation"
    timestamp, cached_data = cache_storage[cache_key]
    cache_storage[cache_key] = (timestamp - 2, cached_data)

    data3 = client.get("/expensive-operation").json()
    assert data1 != data3
    assert expensive_operation_stats["calls"] == 2


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


def test_depends_keeps_none_return_annotation_for_204() -> None:
    test_app = FastAPI()

    @depends
    def with_test() -> None:
        pass

    @test_app.get("/test", status_code=status.HTTP_204_NO_CONTENT)
    @with_test
    async def endpoint() -> None:
        pass

    assert endpoint is not None
    test_client = TestClient(test_app)
    response = test_client.get("/test")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
