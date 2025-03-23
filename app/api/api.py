from fastapi import APIRouter
from app.api.endpoints import health, user

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(user.router, prefix="/api/v1/user", tags=["user"])
# Здесь будет импорт и подключение эндпоинтов
# from app.api.endpoints import items, users
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(items.router, prefix="/items", tags=["items"])
