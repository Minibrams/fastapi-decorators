"""This app JUST tests forward references."""
from __future__ import annotations

from typing import Any

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from tests.forwardrefs.dummy_decorator import empty_decorator


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()

    @app.get("/test")
    @empty_decorator
    def endpoint_with_request_dependency(request: Request) -> str:
        """Test a builtin."""
        return "OK"

    return app


@pytest.fixture
def test_client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_forward_references_are_copied_from_call_site_scope(
    test_client: TestClient,
) -> None:
    response = test_client.get("/test")
    assert response.status_code == 200
    assert response.json() == "OK"
