"""Tests for ProcessingOrchestrator metadata fetching logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.orchestrator_service import ProcessingOrchestrator
from app.models.orm.video import Video


@pytest.fixture
def orchestrator():
    session = AsyncMock()
    ws_manager = MagicMock()
    return ProcessingOrchestrator(session, ws_manager)


class TestOrchestratorMetadataFetch:
    @pytest.mark.asyncio
    async def test_fetch_videos_metadata_success(self, orchestrator):
        # Create a mock Video object
        video = Video(
            youtube_video_id="ntPTTV6jvM4",
            title=None,
            thumbnail_url=None,
            channel_title=None,
            status="pending"
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "QUANTO DINHEIRO PRECISA PARA COMEÇAR A VENDER BRIGADEIROS ?",
            "author_name": "Vitoria Sales",
            "thumbnail_url": "https://i.ytimg.com/vi/ntPTTV6jvM4/hqdefault.jpg"
        }
        
        # Mock httpx.AsyncClient
        class MockAsyncClient:
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
            async def get(self, url):
                return mock_response
                
        with patch("httpx.AsyncClient", return_value=MockAsyncClient()):
            await orchestrator._fetch_videos_metadata([video])
            
        assert video.title == "QUANTO DINHEIRO PRECISA PARA COMEÇAR A VENDER BRIGADEIROS ?"
        assert video.channel_title == "Vitoria Sales"
        assert video.thumbnail_url == "https://i.ytimg.com/vi/ntPTTV6jvM4/hqdefault.jpg"

    @pytest.mark.asyncio
    async def test_fetch_videos_metadata_partial_success(self, orchestrator):
        video1 = Video(
            youtube_video_id="id1",
            title=None,
            thumbnail_url=None,
            channel_title=None
        )
        video2 = Video(
            youtube_video_id="id2",
            title="Existing Title",
            thumbnail_url=None,
            channel_title=None
        )
        
        class MockAsyncClient:
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
            async def get(self, url):
                mock_resp = MagicMock()
                if "id1" in url:
                    mock_resp.status_code = 200
                    mock_resp.json.return_value = {"title": "Title 1"}
                else:
                    mock_resp.status_code = 404
                return mock_resp
                
        with patch("httpx.AsyncClient", return_value=MockAsyncClient()):
            await orchestrator._fetch_videos_metadata([video1, video2])
            
        assert video1.title == "Title 1"
        assert video2.title == "Existing Title"
