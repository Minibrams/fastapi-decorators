"""This app JUST tests forward references."""

from __future__ import annotations
from typing import Annotated

import pytest
from fastapi import FastAPI, Request, Header
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


def test_forward_references_plus_annotation(
    test_client: TestClient,
) -> None:
    @test_client.app.get("/test-extra")
    @empty_decorator
    def endpoint_with_request_dependency(
        request: Request,
        requestor_id: Annotated[str, Header(alias="requestor_id")],
    ) -> str:
        """Test a builtin."""
        return "OK"

    headers = {"requestor_id": "potato@me"}
    response = test_client.get("/test-extra", headers=headers)
    assert response.status_code == 200
    assert response.json() == "OK"
