from fastapi import APIRouter
from app.api.endpoints import health

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
# Здесь будет импорт и подключение эндпоинтов
# from app.api.endpoints import items, users
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(items.router, prefix="/items", tags=["items"])
