import pytest
import uuid
from datetime import datetime, timedelta
import base64
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import Promotion, Product, Category

# Sample test image as base64
TEST_IMAGE_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="


@pytest.fixture
async def test_category(async_session: AsyncSession):
    category = Category(name="Test Category")
    async_session.add(category)
    await async_session.commit()
    await async_session.refresh(category)
    return category


@pytest.fixture
async def test_product(async_session: AsyncSession, test_category):
    product = Product(
        name="Test Product",
        category_id=test_category.category_id,
        price=99.99,
        rating=4.5
    )
    async_session.add(product)
    await async_session.commit()
    await async_session.refresh(product)
    return product


@pytest.fixture
async def test_products(async_session: AsyncSession, test_category):
    products = []
    for i in range(3):
        product = Product(
            name=f"Test Product {i}",
            category_id=test_category.category_id,
            price=50.0 + i * 10,
            rating=4.0 + i * 0.2
        )
        async_session.add(product)
        products.append(product)
    
    await async_session.commit()
    for product in products:
        await async_session.refresh(product)
    
    return products


@pytest.fixture
async def test_promotion(async_session: AsyncSession, test_product):
    now = datetime.now()
    promotion = Promotion(
        name="Test Promotion",
        description="This is a test promotion",
        url="https://example.com/promo",
        image_url="/static/images/promotions/test.jpg",
        image_path="/path/to/image.jpg",
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=7)
    )
    promotion.products.append(test_product)
    
    async_session.add(promotion)
    await async_session.commit()
    await async_session.refresh(promotion)
    return promotion


@pytest.fixture
async def test_promotions(async_session: AsyncSession, test_products):
    now = datetime.now()
    promotions = []
    
    # Active promotion
    active_promo = Promotion(
        name="Active Promotion",
        description="This promotion is currently active",
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=7)
    )
    active_promo.products.append(test_products[0])
    
    # Future promotion
    future_promo = Promotion(
        name="Future Promotion",
        description="This promotion starts in the future",
        start_date=now + timedelta(days=1),
        end_date=now + timedelta(days=14)
    )
    future_promo.products.append(test_products[1])
    
    # Expired promotion
    expired_promo = Promotion(
        name="Expired Promotion",
        description="This promotion has already ended",
        start_date=now - timedelta(days=14),
        end_date=now - timedelta(days=1)
    )
    expired_promo.products.append(test_products[2])
    
    promotions.extend([active_promo, future_promo, expired_promo])
    for promo in promotions:
        async_session.add(promo)
    
    await async_session.commit()
    for promo in promotions:
        await async_session.refresh(promo)
    
    return promotions


# Test creating a promotion
@pytest.mark.asyncio
async def test_create_promotion(
    async_client: AsyncClient,
    auth_headers: dict,
    test_product
):
    # Arrange
    now = datetime.now()
    payload = {
        "name": "New Promotion",
        "description": "This is a brand new promotion",
        "url": "https://example.com/new-promo",
        "start_date": (now - timedelta(days=1)).isoformat(),
        "end_date": (now + timedelta(days=10)).isoformat(),
        "image_base64": TEST_IMAGE_BASE64,
        "product_ids": [str(test_product.product_id)]
    }
    
    # Act
    response = await async_client.post(
        "/api/v1/promotion",
        json=payload,
        headers=auth_headers
    )
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]
    assert data["url"] == payload["url"]
    assert len(data["products"]) == 1
    assert data["products"][0]["product_id"] == str(test_product.product_id)
    assert data["image_url"] is not None


# Test listing promotions
@pytest.mark.asyncio
async def test_list_promotions(
    async_client: AsyncClient,
    test_promotions
):
    # Act
    response = await async_client.get("/api/v1/promotion")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


# Test filtering active promotions
@pytest.mark.asyncio
async def test_list_active_promotions(
    async_client: AsyncClient,
    test_promotions
):
    # Act
    response = await async_client.get("/api/v1/promotion?active_only=true")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Active Promotion"


# Test filtering promotions by product
@pytest.mark.asyncio
async def test_list_promotions_by_product(
    async_client: AsyncClient,
    test_promotions,
    test_products
):
    # Act
    product_id = test_products[0].product_id
    response = await async_client.get(f"/api/v1/promotion?product_id={product_id}")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Active Promotion"


# Test get promotion by ID
@pytest.mark.asyncio
async def test_get_promotion(
    async_client: AsyncClient,
    test_promotion
):
    # Act
    response = await async_client.get(f"/api/v1/promotion/{test_promotion.promotion_id}")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["promotion_id"] == str(test_promotion.promotion_id)
    assert data["name"] == test_promotion.name
    assert data["description"] == test_promotion.description


# Test get nonexistent promotion
@pytest.mark.asyncio
async def test_get_nonexistent_promotion(async_client: AsyncClient):
    # Arrange
    nonexistent_id = uuid.uuid4()
    
    # Act
    response = await async_client.get(f"/api/v1/promotion/{nonexistent_id}")
    
    # Assert
    assert response.status_code == 404


# Test update promotion
@pytest.mark.asyncio
async def test_update_promotion(
    async_client: AsyncClient,
    auth_headers: dict,
    test_promotion,
    test_products
):
    # Arrange
    update_data = {
        "name": "Updated Promotion Name",
        "description": "Updated description",
        "product_ids": [str(p.product_id) for p in test_products]
    }
    
    # Act
    response = await async_client.put(
        f"/api/v1/promotion/{test_promotion.promotion_id}",
        json=update_data,
        headers=auth_headers
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    assert len(data["products"]) == len(test_products)


# Test delete promotion
@pytest.mark.asyncio
async def test_delete_promotion(
    async_client: AsyncClient,
    auth_headers: dict,
    test_promotion,
    async_session: AsyncSession
):
    # Act - Delete the promotion
    response = await async_client.delete(
        f"/api/v1/promotion/{test_promotion.promotion_id}",
        headers=auth_headers
    )
    
    # Assert - Should return 204 No Content
    assert response.status_code == 204
    
    # Verify the promotion was soft-deleted
    from sqlalchemy import select
    stmt = select(Promotion).where(Promotion.promotion_id == test_promotion.promotion_id)
    result = await async_session.execute(stmt)
    deleted_promo = result.scalar_one_or_none()
    
    assert deleted_promo is not None
    assert deleted_promo.deleted_at is not None


# Test update promotion products
@pytest.mark.asyncio
async def test_update_promotion_products(
    async_client: AsyncClient,
    auth_headers: dict,
    test_promotion,
    test_products
):
    # Arrange
    product_ids = [str(p.product_id) for p in test_products]
    payload = {
        "product_ids": product_ids
    }
    
    # Act
    response = await async_client.post(
        f"/api/v1/promotion/{test_promotion.promotion_id}/products",
        json=payload,
        headers=auth_headers
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data["products"]) == len(test_products)
    response_product_ids = [p["product_id"] for p in data["products"]]
    for pid in product_ids:
        assert pid in response_product_ids


# Test get active promotions
@pytest.mark.asyncio
async def test_get_active_promotions(
    async_client: AsyncClient,
    test_promotions
):
    # Act
    response = await async_client.get("/api/v1/promotion/active")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Active Promotion"


# Test get promotions by product
@pytest.mark.asyncio
async def test_get_promotions_by_product(
    async_client: AsyncClient,
    test_promotions,
    test_products
):
    # Arrange
    product_id = test_products[0].product_id
    
    # Act
    response = await async_client.get(f"/api/v1/promotion/product/{product_id}")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Active Promotion"


# Test validation for date ranges
@pytest.mark.asyncio
async def test_promotion_date_validation(
    async_client: AsyncClient,
    auth_headers: dict
):
    # Arrange
    now = datetime.now()
    payload = {
        "name": "Invalid Date Promotion",
        "description": "This promotion has invalid dates",
        "start_date": (now + timedelta(days=10)).isoformat(),  # Start date after end date
        "end_date": (now).isoformat(),
    }
    
    # Act
    response = await async_client.post(
        "/api/v1/promotion",
        json=payload,
        headers=auth_headers
    )
    
    # Assert
    assert response.status_code == 422  # Validation error


# Test unauthorized access
@pytest.mark.asyncio
async def test_unauthorized_create_promotion(
    async_client: AsyncClient,
    test_product
):
    # Arrange
    now = datetime.now()
    payload = {
        "name": "New Promotion",
        "description": "This is a brand new promotion",
        "start_date": (now - timedelta(days=1)).isoformat(),
        "end_date": (now + timedelta(days=10)).isoformat(),
        "product_ids": [str(test_product.product_id)]
    }
    
    # Act - No auth headers
    response = await async_client.post(
        "/api/v1/promotion",
        json=payload
    )
    
    # Assert
    assert response.status_code == 403  # Forbidden


# Test creating promotion with nonexistent product
@pytest.mark.asyncio
async def test_create_promotion_with_nonexistent_product(
    async_client: AsyncClient,
    auth_headers: dict
):
    # Arrange
    now = datetime.now()
    nonexistent_product_id = uuid.uuid4()
    payload = {
        "name": "New Promotion",
        "description": "This is a brand new promotion",
        "start_date": (now - timedelta(days=1)).isoformat(),
        "end_date": (now + timedelta(days=10)).isoformat(),
        "product_ids": [str(nonexistent_product_id)]
    }
    
    # Act
    response = await async_client.post(
        "/api/v1/promotion",
        json=payload,
        headers=auth_headers
    )
    
    # Assert - Should still create the promotion, just without products
    assert response.status_code == 201
    data = response.json()
    assert len(data["products"]) == 0
