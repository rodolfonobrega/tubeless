"""API v1 package."""

from fastapi import APIRouter

from app.api.v1.chat import router as chat_router
from app.api.v1.projects import router as projects_router
from app.api.v1.search import router as search_router
from app.api.v1.settings import router as settings_router
from app.api.v1.videos import router as videos_router

router = APIRouter()

# Include all sub-routers
router.include_router(search_router, tags=["search"])
router.include_router(projects_router, prefix="/projects", tags=["projects"])
router.include_router(videos_router, prefix="/videos", tags=["videos"])
router.include_router(chat_router, prefix="/chat", tags=["chat"])
router.include_router(settings_router, tags=["settings"])
