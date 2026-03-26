"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from hybrid_sentinel.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
