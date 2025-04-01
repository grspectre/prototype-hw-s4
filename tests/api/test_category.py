import pytest
from uuid import UUID
from httpx import AsyncClient
from fastapi import status
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import Category
import logging

LOGGER = logging.Logger(__name__, level=logging.WARN)

@pytest.fixture
async def test_category(async_session: AsyncSession):
    """Создает тестовую категорию."""
    category = Category(name="Test Category")
    async_session.add(category)
    await async_session.commit()
    await async_session.refresh(category)
    return category


@pytest.mark.asyncio
async def test_get_categories_empty(async_client: AsyncClient):
    """Тест получения пустого списка категорий."""
    response = await async_client.get("/api/v1/category")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_get_categories_with_data(async_client: AsyncClient, test_category: Category):
    """Тест получения списка категорий с данными."""
    response = await async_client.get("/api/v1/category")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert data["items"][0]["name"] == test_category.name
    assert UUID(data["items"][0]["category_id"]) == test_category.category_id


@pytest.mark.asyncio
async def test_get_category_by_id(async_client: AsyncClient, test_category: Category):
    """Тест получения категории по ID."""
    response = await async_client.get(f"/api/v1/category/{test_category.category_id}")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == test_category.name
    assert UUID(data["category_id"]) == test_category.category_id


@pytest.mark.asyncio
async def test_get_category_not_found(async_client: AsyncClient):
    """Тест получения несуществующей категории."""
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    response = await async_client.get(f"/api/v1/category/{non_existent_id}")
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_category_unauthorized(async_client: AsyncClient):
    """Тест создания категории без авторизации."""
    category_data = {"name": "Unauthorized Category"}
    
    response = await async_client.post("/api/v1/category", json=category_data)
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_create_category(async_client: AsyncClient, auth_headers: dict):
    LOGGER.warning(auth_headers)
    """Тест создания категории."""
    category_data = {"name": "New Category"}
    
    response = await async_client.post(
        "/api/v1/category", 
        json=category_data,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == category_data["name"]
    assert "category_id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_duplicate_category(async_client: AsyncClient, test_category: Category, auth_headers: dict):
    """Тест создания категории с уже существующим именем."""
    category_data = {"name": test_category.name}
    
    response = await async_client.post(
        "/api/v1/category", 
        json=category_data,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_category(async_client: AsyncClient, test_category: Category, auth_headers: dict):
    """Тест обновления категории."""
    update_data = {"name": "Updated Category Name"}
    
    response = await async_client.put(
        f"/api/v1/category/{test_category.category_id}", 
        json=update_data,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == update_data["name"]
    assert UUID(data["category_id"]) == test_category.category_id


@pytest.mark.asyncio
async def test_update_category_not_found(async_client: AsyncClient, auth_headers: dict):
    """Тест обновления несуществующей категории."""
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    update_data = {"name": "Not Found Category"}
    
    response = await async_client.put(
        f"/api/v1/category/{non_existent_id}", 
        json=update_data,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_category_to_existing_name(
    async_client: AsyncClient, 
    test_category: Category, 
    auth_headers: dict,
    async_session: AsyncSession
):
    """Тест обновления категории с уже существующим именем."""
    # Создаем вторую категорию
    second_category = Category(name="Second Category")
    async_session.add(second_category)
    await async_session.commit()
    await async_session.refresh(second_category)
    
    # Пытаемся обновить первую категорию именем второй
    update_data = {"name": second_category.name}
    
    response = await async_client.put(
        f"/api/v1/category/{test_category.category_id}", 
        json=update_data,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_category(async_client: AsyncClient, test_category: Category, auth_headers: dict):
    """Тест удаления категории."""
    response = await async_client.delete(
        f"/api/v1/category/{test_category.category_id}",
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Проверяем, что категория действительно удалена (soft delete)
    get_response = await async_client.get(f"/api/v1/category/{test_category.category_id}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_category_not_found(async_client: AsyncClient, auth_headers: dict):
    """Тест удаления несуществующей категории."""
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    
    response = await async_client.delete(
        f"/api/v1/category/{non_existent_id}",
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_pagination(async_client: AsyncClient, async_session: AsyncSession):
    """Тест пагинации списка категорий."""
    # Создаем несколько категорий для тестирования пагинации
    categories = [Category(name=f"Category {i}") for i in range(1, 12)]  # Создаем 11 категорий
    for cat in categories:
        async_session.add(cat)
    await async_session.commit()
    
    # Запрос первой страницы с 5 элементами
    response1 = await async_client.get("/api/v1/category?page=1&page_size=5")
    data1 = response1.json()
    
    assert response1.status_code == status.HTTP_200_OK
    assert data1["total"] >= 11
    assert len(data1["items"]) == 5
    assert data1["page"] == 1
    assert data1["page_size"] == 5
    
    # Запрос второй страницы с 5 элементами
    response2 = await async_client.get("/api/v1/category?page=2&page_size=5")
    data2 = response2.json()
    
    assert response2.status_code == status.HTTP_200_OK
    assert data2["total"] >= 11
    assert len(data2["items"]) == 5
    assert data2["page"] == 2
    assert data2["page_size"] == 5
    
    # Проверка, что категории на разных страницах разные
    page1_ids = [item["category_id"] for item in data1["items"]]
    page2_ids = [item["category_id"] for item in data2["items"]]
    assert not any(id in page2_ids for id in page1_ids)
