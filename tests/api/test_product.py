import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import Product, Category
from datetime import datetime

# Test data fixtures
@pytest.fixture(scope="function")
async def test_category(async_session: AsyncSession):
    # Create a test category
    category = Category(
        name="Test Category"
    )
    async_session.add(category)
    await async_session.commit()
    await async_session.refresh(category)
    
    yield category
    
    # Clean up is handled by session rollback

@pytest.fixture(scope="function")
async def test_products(async_session: AsyncSession, test_category):
    # Create multiple test products for listing and filtering tests
    products = [
        Product(
            name="Test Product 1",
            category_id=test_category.category_id,
            price=10.99,
            rating=4.5
        ),
        Product(
            name="Test Product 2",
            category_id=test_category.category_id,
            price=20.99,
            rating=3.5
        ),
        Product(
            name="Budget Item",
            category_id=test_category.category_id,
            price=5.99,
            rating=4.0
        ),
        Product(
            name="Premium Product",
            category_id=test_category.category_id,
            price=99.99,
            rating=5.0
        )
    ]
    
    for product in products:
        async_session.add(product)
    
    await async_session.commit()
    
    # Refresh all products to get their IDs
    refreshed_products = []
    for product in products:
        await async_session.refresh(product)
        refreshed_products.append(product)
    
    yield refreshed_products
    
    # Clean up is handled by session rollback

@pytest.mark.asyncio
async def test_create_product(async_client: AsyncClient, test_category, auth_headers):
    """Test creating a new product"""
    product_data = {
        "name": "New Test Product",
        "price": 15.99,
        "category_id": str(test_category.category_id)
    }
    
    response = await async_client.post(
        "/api/v1/product", 
        json=product_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == product_data["name"]
    assert data["price"] == product_data["price"]
    assert data["category_id"] == product_data["category_id"]
    assert "product_id" in data
    assert "created_at" in data
    assert "updated_at" in data

@pytest.mark.asyncio
async def test_create_product_with_invalid_category(async_client: AsyncClient, auth_headers):
    """Test creating a product with non-existent category ID"""
    product_data = {
        "name": "Invalid Category Product",
        "price": 15.99,
        "category_id": str(uuid.uuid4())  # Random non-existent UUID
    }
    
    response = await async_client.post(
        "/api/v1/product", 
        json=product_data,
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_create_product_unauthorized(async_client: AsyncClient, test_category):
    """Test creating a product without authentication"""
    product_data = {
        "name": "Unauthorized Product",
        "price": 15.99,
        "category_id": str(test_category.category_id)
    }
    
    response = await async_client.post("/api/v1/product", json=product_data)
    
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_list_products(async_client: AsyncClient, test_products):
    """Test listing all products with pagination"""
    response = await async_client.get("/api/v1/product")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "pages" in data
    
    assert data["total"] >= len(test_products)
    
    # Verify first page has correct number of items
    assert len(data["items"]) <= data["page_size"]
    
    # Check if products have the expected fields
    for product in data["items"]:
        assert "product_id" in product
        assert "name" in product
        assert "price" in product
        assert "category_id" in product
        assert "rating" in product

@pytest.mark.asyncio
async def test_list_products_with_pagination(async_client: AsyncClient, test_products):
    """Test product listing with custom pagination parameters"""
    response = await async_client.get("/api/v1/product?page=1&page_size=2")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2

@pytest.mark.asyncio
async def test_list_products_with_filters(async_client: AsyncClient, test_products):
    """Test filtering products by various parameters"""
    # Filter by min_price
    response = await async_client.get("/api/v1/product?min_price=20")
    assert response.status_code == 200
    data = response.json()
    for product in data["items"]:
        assert product["price"] >= 20
    
    # Filter by max_price
    response = await async_client.get("/api/v1/product?max_price=15")
    assert response.status_code == 200
    data = response.json()
    for product in data["items"]:
        assert product["price"] <= 15
    
    # Filter by min_rating
    response = await async_client.get("/api/v1/product?min_rating=4.5")
    assert response.status_code == 200
    data = response.json()
    for product in data["items"]:
        assert product["rating"] >= 4.5
    
    # Filter by name
    response = await async_client.get("/api/v1/product?name=Budget")
    assert response.status_code == 200
    data = response.json()
    assert all("Budget" in product["name"] for product in data["items"])

@pytest.mark.asyncio
async def test_get_product_detail(async_client: AsyncClient, test_products):
    """Test getting detailed information for a specific product"""
    test_product = test_products[0]
    
    response = await async_client.get(f"/api/v1/product/{test_product.product_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["product_id"] == str(test_product.product_id)
    assert data["name"] == test_product.name
    assert data["price"] == test_product.price
    assert data["rating"] == test_product.rating
    assert "category" in data
    assert data["category"]["category_id"] == str(test_product.category_id)

@pytest.mark.asyncio
async def test_get_nonexistent_product(async_client: AsyncClient):
    """Test getting a product that doesn't exist"""
    nonexistent_id = uuid.uuid4()
    
    response = await async_client.get(f"/api/v1/product/{nonexistent_id}")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_product(async_client: AsyncClient, test_products, auth_headers):
    """Test updating a product's details"""
    test_product = test_products[0]
    
    update_data = {
        "name": "Updated Product Name",
        "price": 25.99
    }
    
    response = await async_client.put(
        f"/api/v1/product/{test_product.product_id}",
        json=update_data,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["product_id"] == str(test_product.product_id)
    assert data["name"] == update_data["name"]
    assert data["price"] == update_data["price"]
    # Category should remain unchanged
    assert data["category_id"] == str(test_product.category_id)

@pytest.mark.asyncio
async def test_update_product_category(async_client: AsyncClient, test_products, test_category, auth_headers, async_session):
    """Test updating a product's category"""
    test_product = test_products[0]
    
    # Create a new category
    new_category = Category(name="New Test Category")
    async_session.add(new_category)
    await async_session.commit()
    await async_session.refresh(new_category)
    
    update_data = {
        "category_id": str(new_category.category_id)
    }
    
    response = await async_client.put(
        f"/api/v1/product/{test_product.product_id}",
        json=update_data,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["product_id"] == str(test_product.product_id)
    assert data["category_id"] == str(new_category.category_id)

@pytest.mark.asyncio
async def test_update_nonexistent_product(async_client: AsyncClient, auth_headers):
    """Test updating a product that doesn't exist"""
    nonexistent_id = uuid.uuid4()
    
    update_data = {
        "name": "This Will Fail",
        "price": 99.99
    }
    
    response = await async_client.put(
        f"/api/v1/product/{nonexistent_id}",
        json=update_data,
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_product_unauthorized(async_client: AsyncClient, test_products):
    """Test updating a product without authentication"""
    test_product = test_products[0]
    
    update_data = {
        "name": "Unauthorized Update",
        "price": 33.33
    }
    
    response = await async_client.put(
        f"/api/v1/product/{test_product.product_id}",
        json=update_data
    )
    
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_delete_product(async_client: AsyncClient, test_products, auth_headers, async_session):
    """Test soft-deleting a product"""
    test_product = test_products[0]
    
    response = await async_client.delete(
        f"/api/v1/product/{test_product.product_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 204
    
    # Verify product is soft-deleted (deleted_at is set)
    # We need to refresh our session first
    await async_session.refresh(test_product)
    assert test_product.deleted_at is not None
    
    # Verify product no longer appears in list
    list_response = await async_client.get("/api/v1/product")
    products = list_response.json()["items"]
    product_ids = [p["product_id"] for p in products]
    assert str(test_product.product_id) not in product_ids

@pytest.mark.asyncio
async def test_delete_nonexistent_product(async_client: AsyncClient, auth_headers):
    """Test deleting a product that doesn't exist"""
    nonexistent_id = uuid.uuid4()
    
    response = await async_client.delete(
        f"/api/v1/product/{nonexistent_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_product_unauthorized(async_client: AsyncClient, test_products):
    """Test deleting a product without authentication"""
    test_product = test_products[0]
    
    response = await async_client.delete(
        f"/api/v1/product/{test_product.product_id}"
    )
    
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_list_products_by_category(async_client: AsyncClient, test_products, test_category):
    """Test listing products filtered by category"""
    response = await async_client.get(f"/api/v1/product/category/{test_category.category_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "items" in data
    assert data["total"] > 0
    
    # All products should be from the specified category
    for product in data["items"]:
        assert product["category_id"] == str(test_category.category_id)

@pytest.mark.asyncio
async def test_list_products_by_nonexistent_category(async_client: AsyncClient):
    """Test listing products for a category that doesn't exist"""
    nonexistent_id = uuid.uuid4()
    
    response = await async_client.get(f"/api/v1/product/category/{nonexistent_id}")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_search_products(async_client: AsyncClient, test_products):
    """Test searching for products by name"""
    # Create a product with a distinctive name to search for
    search_term = "Premium"
    
    response = await async_client.get(f"/api/v1/product/search?query={search_term}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "items" in data
    assert data["total"] > 0
    
    # All returned products should contain the search term in their name
    for product in data["items"]:
        assert search_term.lower() in product["name"].lower()

@pytest.mark.asyncio
async def test_search_products_with_filters(async_client: AsyncClient, test_products, test_category):
    """Test searching for products with additional filters"""
    search_term = "Product"
    min_price = 15.0
    
    response = await async_client.get(
        f"/api/v1/product/search?query={search_term}&min_price={min_price}&category_id={test_category.category_id}"
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify filters are applied correctly
    for product in data["items"]:
        assert search_term.lower() in product["name"].lower()
        assert product["price"] >= min_price
        assert product["category_id"] == str(test_category.category_id)

@pytest.mark.asyncio
async def test_search_products_no_results(async_client: AsyncClient):
    """Test searching for products with no matches"""
    search_term = "NonExistentProductXYZ"
    
    response = await async_client.get(f"/api/v1/product/search?query={search_term}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 0
    assert len(data["items"]) == 0
