"""Tests for /api/v1/projects/ endpoints with mocked repositories."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import make_project

PROJECTS_URL = "/api/v1/projects"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patch_repos(mock_proj_repo=None, mock_video_repo=None):
    """Context manager patching both repo classes in the projects module."""
    return (
        patch("app.api.v1.projects.ProjectRepository", return_value=mock_proj_repo or MagicMock()),
        patch("app.api.v1.projects.VideoRepository", return_value=mock_video_repo or MagicMock()),
    )


# ---------------------------------------------------------------------------
# POST /projects/
# ---------------------------------------------------------------------------

class TestCreateProject:
    def test_creates_project_returns_201(self, client):
        project = make_project(name="My Project", query="test query")
        mock_proj_repo = AsyncMock()
        mock_proj_repo.create = AsyncMock(return_value=project)
        mock_video_repo = AsyncMock()
        mock_video_repo.create = AsyncMock()

        with patch("app.api.v1.projects.ProjectRepository", return_value=mock_proj_repo), \
             patch("app.api.v1.projects.VideoRepository", return_value=mock_video_repo):
            response = client.post(PROJECTS_URL, json={
                "name": "My Project",
                "query": "test query",
                "video_ids": ["abc123"],
            })

        assert response.status_code == 201

    def test_create_returns_project_fields(self, client):
        project = make_project(name="Test", query="some query")
        mock_proj_repo = AsyncMock()
        mock_proj_repo.create = AsyncMock(return_value=project)
        mock_video_repo = AsyncMock()
        mock_video_repo.create = AsyncMock()

        with patch("app.api.v1.projects.ProjectRepository", return_value=mock_proj_repo), \
             patch("app.api.v1.projects.VideoRepository", return_value=mock_video_repo):
            response = client.post(PROJECTS_URL, json={
                "name": "Test",
                "query": "some query",
                "video_ids": ["v1"],
            })

        data = response.json()
        assert data["name"] == "Test"
        assert data["query"] == "some query"
        assert data["status"] == "pending"
        assert "id" in data
        assert "created_at" in data

    def test_create_calls_video_repo_once_per_video_id(self, client):
        project = make_project()
        mock_proj_repo = AsyncMock()
        mock_proj_repo.create = AsyncMock(return_value=project)
        mock_video_repo = AsyncMock()
        mock_video_repo.create = AsyncMock()

        with patch("app.api.v1.projects.ProjectRepository", return_value=mock_proj_repo), \
             patch("app.api.v1.projects.VideoRepository", return_value=mock_video_repo):
            client.post(PROJECTS_URL, json={
                "name": "Project",
                "query": "query",
                "video_ids": ["v1", "v2", "v3"],
            })

        assert mock_video_repo.create.call_count == 3

    def test_create_requires_name(self, client):
        response = client.post(PROJECTS_URL, json={
            "query": "query",
            "video_ids": ["v1"],
        })
        assert response.status_code == 422

    def test_create_requires_query(self, client):
        response = client.post(PROJECTS_URL, json={
            "name": "Project",
            "video_ids": ["v1"],
        })
        assert response.status_code == 422

    def test_create_requires_at_least_one_video_id(self, client):
        response = client.post(PROJECTS_URL, json={
            "name": "Project",
            "query": "query",
            "video_ids": [],
        })
        assert response.status_code == 422

    def test_create_rejects_empty_name(self, client):
        response = client.post(PROJECTS_URL, json={
            "name": "",
            "query": "query",
            "video_ids": ["v1"],
        })
        assert response.status_code == 422

    def test_create_returns_500_on_repo_error(self, client):
        mock_proj_repo = AsyncMock()
        mock_proj_repo.create = AsyncMock(side_effect=Exception("DB error"))

        with patch("app.api.v1.projects.ProjectRepository", return_value=mock_proj_repo), \
             patch("app.api.v1.projects.VideoRepository", return_value=AsyncMock()):
            response = client.post(PROJECTS_URL, json={
                "name": "Project",
                "query": "query",
                "video_ids": ["v1"],
            })

        assert response.status_code == 500


# ---------------------------------------------------------------------------
# GET /projects/
# ---------------------------------------------------------------------------

class TestListProjects:
    def test_list_returns_200(self, client):
        mock_proj_repo = AsyncMock()
        mock_proj_repo.list_all = AsyncMock(return_value=[make_project()])
        mock_proj_repo.count = AsyncMock(return_value=1)

        with patch("app.api.v1.projects.ProjectRepository", return_value=mock_proj_repo):
            response = client.get(PROJECTS_URL)

        assert response.status_code == 200

    def test_list_returns_projects_and_total(self, client):
        projects = [make_project(name=f"Project {i}") for i in range(3)]
        mock_proj_repo = AsyncMock()
        mock_proj_repo.list_all = AsyncMock(return_value=projects)
        mock_proj_repo.count = AsyncMock(return_value=3)

        with patch("app.api.v1.projects.ProjectRepository", return_value=mock_proj_repo):
            response = client.get(PROJECTS_URL)

        data = response.json()
        assert data["total"] == 3
        assert len(data["projects"]) == 3

    def test_list_empty_projects(self, client):
        mock_proj_repo = AsyncMock()
        mock_proj_repo.list_all = AsyncMock(return_value=[])
        mock_proj_repo.count = AsyncMock(return_value=0)

        with patch("app.api.v1.projects.ProjectRepository", return_value=mock_proj_repo):
            response = client.get(PROJECTS_URL)

        data = response.json()
        assert data["total"] == 0
        assert data["projects"] == []

    def test_list_passes_offset_and_limit(self, client):
        mock_proj_repo = AsyncMock()
        mock_proj_repo.list_all = AsyncMock(return_value=[])
        mock_proj_repo.count = AsyncMock(return_value=0)

        with patch("app.api.v1.projects.ProjectRepository", return_value=mock_proj_repo):
            client.get(PROJECTS_URL + "?offset=10&limit=5")

        mock_proj_repo.list_all.assert_called_once_with(offset=10, limit=5)


# ---------------------------------------------------------------------------
# GET /projects/{project_id}
# ---------------------------------------------------------------------------

class TestGetProject:
    def test_get_returns_project(self, client):
        project = make_project(name="Found Project")
        project_id = str(project.id)
        mock_proj_repo = AsyncMock()
        mock_proj_repo.get = AsyncMock(return_value=project)

        with patch("app.api.v1.projects.ProjectRepository", return_value=mock_proj_repo):
            response = client.get(f"{PROJECTS_URL}/{project_id}")

        assert response.status_code == 200
        assert response.json()["name"] == "Found Project"

    def test_get_returns_404_when_not_found(self, client):
        mock_proj_repo = AsyncMock()
        mock_proj_repo.get = AsyncMock(return_value=None)
        project_id = str(uuid.uuid4())

        with patch("app.api.v1.projects.ProjectRepository", return_value=mock_proj_repo):
            response = client.get(f"{PROJECTS_URL}/{project_id}")

        assert response.status_code == 404

    def test_get_returns_400_for_invalid_uuid(self, client):
        response = client.get(f"{PROJECTS_URL}/not-a-uuid")
        assert response.status_code == 400

    def test_get_passes_correct_uuid_to_repo(self, client):
        project = make_project()
        project_id = str(project.id)
        mock_proj_repo = AsyncMock()
        mock_proj_repo.get = AsyncMock(return_value=project)

        with patch("app.api.v1.projects.ProjectRepository", return_value=mock_proj_repo):
            client.get(f"{PROJECTS_URL}/{project_id}")

        called_id = mock_proj_repo.get.call_args.args[0]
        assert str(called_id) == project_id


# ---------------------------------------------------------------------------
# DELETE /projects/{project_id}
# ---------------------------------------------------------------------------

class TestDeleteProject:
    def test_delete_returns_204(self, client):
        mock_proj_repo = AsyncMock()
        mock_proj_repo.delete = AsyncMock(return_value=True)
        project_id = str(uuid.uuid4())

        with patch("app.api.v1.projects.ProjectRepository", return_value=mock_proj_repo):
            response = client.delete(f"{PROJECTS_URL}/{project_id}")

        assert response.status_code == 204

    def test_delete_returns_404_when_not_found(self, client):
        mock_proj_repo = AsyncMock()
        mock_proj_repo.delete = AsyncMock(return_value=False)
        project_id = str(uuid.uuid4())

        with patch("app.api.v1.projects.ProjectRepository", return_value=mock_proj_repo):
            response = client.delete(f"{PROJECTS_URL}/{project_id}")

        assert response.status_code == 404

    def test_delete_returns_400_for_invalid_uuid(self, client):
        response = client.delete(f"{PROJECTS_URL}/bad-uuid-here")
        assert response.status_code == 400

    def test_delete_commits_session(self, client, mock_session):
        mock_proj_repo = AsyncMock()
        mock_proj_repo.delete = AsyncMock(return_value=True)
        project_id = str(uuid.uuid4())

        with patch("app.api.v1.projects.ProjectRepository", return_value=mock_proj_repo):
            client.delete(f"{PROJECTS_URL}/{project_id}")

        mock_session.commit.assert_called()
