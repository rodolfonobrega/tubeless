"""Smoke tests for health and root endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    def test_health_check_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_body(self, client):
        response = client.get("/health")
        assert response.json() == {"status": "healthy"}

    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_has_message(self, client):
        data = client.get("/").json()
        assert "message" in data

    def test_root_has_version(self, client):
        data = client.get("/").json()
        assert "version" in data

    def test_openapi_docs_accessible(self, client):
        response = client.get("/docs")
        assert response.status_code == 200
