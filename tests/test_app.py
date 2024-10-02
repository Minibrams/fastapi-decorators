from time import sleep
from fastapi.testclient import TestClient
from app import app, fake_db, rate_limit_store, error_log

client = TestClient(app)

def test_read_items():
    response = client.get("/items/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 2

def test_create_item():
    response = client.post("/items/", json={"name": "NewItem"})
    assert response.status_code == 200
    assert response.headers.get("X-Custom-Header") == "CustomValue"
    data = response.json()
    assert data["message"] == "Item created"
    assert data["item"]["name"] == "NewItem"

def test_read_current_user_unauthorized():
    response = client.get("/users/me")
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Unauthorized"

def test_read_current_user_authorized():
    headers = {"token": "valid_token"}
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user"] == "user_from_token"

def test_generate_report():
    response = client.get("/reports/")
    assert response.status_code == 200
    assert response.headers.get("X-Custom-Header") == "CustomValue"
    data = response.json()
    assert data["report"] == "This is your report"

def test_update_user_success():
    user_id = 1
    new_data = {"name": "John Updated", "email": "john_updated@example.com"}
    response = client.put(f"/users/{user_id}", json=new_data)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == f"User {user_id} updated"
    assert data["user"]["name"] == new_data["name"]
    assert data["user"]["email"] == new_data["email"]

def test_update_user_not_found():
    user_id = 999
    new_data = {"name": "Ghost User", "email": "ghost@example.com"}
    response = client.put(f"/users/{user_id}", json=new_data)
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "User not found"

def test_delete_user_unauthorized():
    user_id = 2
    response = client.delete(f"/users/{user_id}")
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Unauthorized"

def test_delete_user_success():
    user_id = 2
    headers = {"token": "valid_token"}
    response = client.delete(f"/users/{user_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == f"User {user_id} deleted"
    assert user_id not in fake_db["users"]

def test_delete_user_not_found():
    user_id = 999
    headers = {"token": "valid_token"}
    response = client.delete(f"/users/{user_id}", headers=headers)
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "User not found"

def test_rate_limiting():
    rate_limit_store.clear()

    for _ in range(5):
        response = client.get("/limited-endpoint")
        assert response.status_code == 200

    # Sixth request should be rate-limited
    response = client.get("/limited-endpoint")
    assert response.status_code == 429
    assert response.json()["detail"] == "Too Many Requests"

    # Wait for rate limit period to expire
    sleep(6)

    response = client.get("/limited-endpoint")
    assert response.status_code == 200

def test_error_handling_success():
    response = client.get("/may-fail?should_fail=false")
    assert response.status_code == 200
    assert response.json()["message"] == "Operation succeeded"

def test_error_handling_failure():
    error_log.clear()

    response = client.get("/may-fail?should_fail=true")
    assert response.status_code == 500
    assert "An error occurred" in response.json()["detail"]

    # Check that error was logged
    assert len(error_log) == 1
    assert error_log[0]['function'] == 'may_fail_operation'

def test_error_log_endpoint():
    response = client.get("/error-log")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
