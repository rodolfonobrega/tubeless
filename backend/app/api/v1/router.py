"""API router combining all endpoint modules."""

from fastapi import APIRouter

from app.api.v1 import chat, projects, search, settings, videos

api_router = APIRouter()

api_router.include_router(search.router, tags=["search"])
api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(videos.router, tags=["videos"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(settings.router, tags=["settings"])
