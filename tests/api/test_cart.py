import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from app.db.base import Product, Category, CartItem, User


@pytest.fixture
async def test_category(async_session: AsyncSession):
    """Create a test category."""
    category = Category(name="Test Category")
    async_session.add(category)
    await async_session.commit()
    await async_session.refresh(category)
    return category


@pytest.fixture
async def test_product(async_session: AsyncSession, test_category: Category):
    """Create a test product."""
    product = Product(
        name="Test Product",
        price=99.99,
        category_id=test_category.category_id
    )
    async_session.add(product)
    await async_session.commit()
    await async_session.refresh(product)
    return product


@pytest.fixture
async def test_cart_item(async_session: AsyncSession, test_product: Product, session_user: User):
    """Create a test cart item."""
    # Create cart item
    cart_item = CartItem(
        user_id=session_user.user_id,
        product_id=test_product.product_id,
        quantity=2
    )
    async_session.add(cart_item)
    await async_session.commit()
    await async_session.refresh(cart_item)
    return cart_item


class TestCartEndpoints:
    """Test cart API endpoints."""

    @pytest.mark.asyncio
    async def test_add_to_cart(self, async_client: AsyncClient, auth_headers: dict, test_product: Product):
        """Test adding a product to the cart."""
        response = await async_client.post(
            "/api/v1/cart/items",
            headers=auth_headers,
            json={
                "product_id": str(test_product.product_id),
                "quantity": 3
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["product_id"] == str(test_product.product_id)
        assert data["quantity"] == 3
        
        # Test adding the same product again should increase quantity
        response = await async_client.post(
            "/api/v1/cart/items",
            headers=auth_headers,
            json={
                "product_id": str(test_product.product_id),
                "quantity": 2
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["quantity"] == 5  # 3 + 2
    
    @pytest.mark.asyncio
    async def test_add_to_cart_nonexistent_product(self, async_client: AsyncClient, auth_headers: dict):
        """Test adding a non-existent product to the cart."""
        non_existent_id = uuid.uuid4()
        response = await async_client.post(
            "/api/v1/cart/items",
            headers=auth_headers,
            json={
                "product_id": str(non_existent_id),
                "quantity": 1
            }
        )
        
        assert response.status_code == 404
        assert f"Product with ID {non_existent_id}" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_cart_items(self, async_client: AsyncClient, auth_headers: dict, test_cart_item: CartItem):
        """Test getting all cart items."""
        response = await async_client.get(
            "/api/v1/cart/items",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        
        # Check that the item contains product details
        item = next(item for item in data["items"] if item["cart_item_id"] == str(test_cart_item.cart_item_id))
        assert "product" in item
        assert item["product"]["product_id"] == str(test_cart_item.product_id)
    
    @pytest.mark.asyncio
    async def test_get_cart_items_with_filters(self, async_client: AsyncClient, auth_headers: dict, 
                                              test_cart_item: CartItem, test_product: Product):
        """Test getting cart items with filters."""
        # Test filtering by product_id
        response = await async_client.get(
            f"/api/v1/cart/items?product_id={test_product.product_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1
        assert all(item["product_id"] == str(test_product.product_id) for item in data["items"])
        
        # Test filtering by min_quantity
        response = await async_client.get(
            "/api/v1/cart/items?min_quantity=2",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(item["quantity"] >= 2 for item in data["items"])
        
        # Test filtering by max_quantity
        response = await async_client.get(
            "/api/v1/cart/items?max_quantity=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(item["quantity"] <= 10 for item in data["items"])

    @pytest.mark.asyncio
    async def test_get_cart_item_by_id(self, async_client: AsyncClient, auth_headers: dict, test_cart_item: CartItem):
        """Test getting a specific cart item by ID."""
        response = await async_client.get(
            f"/api/v1/cart/items/{test_cart_item.cart_item_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["cart_item_id"] == str(test_cart_item.cart_item_id)
        assert data["product_id"] == str(test_cart_item.product_id)
        assert data["quantity"] == test_cart_item.quantity
        assert "product" in data
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_cart_item(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting a non-existent cart item."""
        non_existent_id = uuid.uuid4()
        response = await async_client.get(
            f"/api/v1/cart/items/{non_existent_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert f"Cart item with ID {non_existent_id}" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_cart_item(self, async_client: AsyncClient, auth_headers: dict, test_cart_item: CartItem):
        """Test updating a cart item's quantity."""
        response = await async_client.put(
            f"/api/v1/cart/items/{test_cart_item.cart_item_id}",
            headers=auth_headers,
            json={"quantity": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == 10
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_cart_item(self, async_client: AsyncClient, auth_headers: dict):
        """Test updating a non-existent cart item."""
        non_existent_id = uuid.uuid4()
        response = await async_client.put(
            f"/api/v1/cart/items/{non_existent_id}",
            headers=auth_headers,
            json={"quantity": 5}
        )
        
        assert response.status_code == 404
        assert f"Cart item with ID {non_existent_id}" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_cart_item(self, async_client: AsyncClient, auth_headers: dict, 
                                   async_session: AsyncSession, test_product: Product):
        """Test removing an item from the cart."""
        # First add a new cart item
        response = await async_client.post(
            "/api/v1/cart/items",
            headers=auth_headers,
            json={
                "product_id": str(test_product.product_id),
                "quantity": 1
            }
        )
        
        cart_item_id = response.json()["cart_item_id"]
        
        # Now delete it
        response = await async_client.delete(
            f"/api/v1/cart/items/{cart_item_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
        
        # Verify it's deleted
        response = await async_client.get(
            f"/api/v1/cart/items/{cart_item_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_cart_item(self, async_client: AsyncClient, auth_headers: dict):
        """Test deleting a non-existent cart item."""
        non_existent_id = uuid.uuid4()
        response = await async_client.delete(
            f"/api/v1/cart/items/{non_existent_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert f"Cart item with ID {non_existent_id}" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_clear_cart(self, async_client: AsyncClient, auth_headers: dict, test_cart_item: CartItem):
        """Test clearing the entire cart."""
        # First verify we have items in the cart
        response = await async_client.get(
            "/api/v1/cart/items",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["total"] > 0
        
        # Clear the cart
        response = await async_client.delete(
            "/api/v1/cart/items",
            headers=auth_headers
        )
        
        assert response.status_code == 204
        
        # Verify cart is empty
        response = await async_client.get(
            "/api/v1/cart/items",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["total"] == 0
        assert len(response.json()["items"]) == 0

    @pytest.mark.asyncio
    async def test_get_cart_item_count(self, async_client: AsyncClient, auth_headers: dict, 
                                     async_session: AsyncSession, test_product: Product):
        """Test getting the total count of items in the cart."""
        # First clear the cart
        await async_client.delete(
            "/api/v1/cart/items",
            headers=auth_headers
        )
        
        # Add items with different quantities
        await async_client.post(
            "/api/v1/cart/items",
            headers=auth_headers,
            json={"product_id": str(test_product.product_id), "quantity": 3}
        )
        
        # Get the count
        response = await async_client.get(
            "/api/v1/cart/count",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json() == 3
        
        # Add more items
        await async_client.post(
            "/api/v1/cart/items",
            headers=auth_headers,
            json={"product_id": str(test_product.product_id), "quantity": 2}
        )
        
        # Check count again
        response = await async_client.get(
            "/api/v1/cart/count",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json() == 5  # 3 + 2
    
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, async_client: AsyncClient, test_cart_item: CartItem):
        """Test accessing cart endpoints without authentication."""
        endpoints = [
            ("GET", "/api/v1/cart/items"),
            ("POST", "/api/v1/cart/items"),
            ("GET", f"/api/v1/cart/items/{test_cart_item.cart_item_id}"),
            ("PUT", f"/api/v1/cart/items/{test_cart_item.cart_item_id}"),
            ("DELETE", f"/api/v1/cart/items/{test_cart_item.cart_item_id}"),
            ("DELETE", "/api/v1/cart/items"),
            ("GET", "/api/v1/cart/count")
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = await async_client.get(endpoint)
            elif method == "POST":
                response = await async_client.post(
                    endpoint, 
                    json={"product_id": str(uuid.uuid4()), "quantity": 1}
                )
            elif method == "PUT":
                response = await async_client.put(
                    endpoint, 
                    json={"quantity": 5}
                )
            elif method == "DELETE":
                response = await async_client.delete(endpoint)
            
            assert response.status_code in (401, 403), f"Endpoint {method} {endpoint} should require authentication"
