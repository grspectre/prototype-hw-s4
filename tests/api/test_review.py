import uuid
import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import datetime

# Test data
test_product_id = str(uuid.uuid4())
test_review_id = str(uuid.uuid4())

@pytest.fixture(scope="function")
async def test_category(async_client: AsyncClient, auth_headers: dict):
    """Create a test category for products"""
    response = await async_client.post(
        "/api/v1/category/",
        json={"name": "Test Category"},
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()

@pytest.fixture(scope="function")
async def test_product(async_client: AsyncClient, auth_headers: dict, test_category):
    """Create a test product for reviews"""
    response = await async_client.post(
        "/api/v1/product/",
        json={
            "name": "Test Product",
            "price": 99.99,
            "category_id": test_category["category_id"]
        },
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()

@pytest.fixture(scope="function")
async def test_review(async_client: AsyncClient, auth_headers: dict, test_product):
    """Create a test review"""
    response = await async_client.post(
        "/api/v1/review/",
        json={
            "product_id": test_product["product_id"],
            "text": "This is a test review",
            "rating": 5
        },
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    return response.json()


class TestReviewEndpoints:
    @pytest.mark.asyncio
    async def test_create_review(self, async_client: AsyncClient, auth_headers: dict, test_product):
        """Test creating a new review"""
        response = await async_client.post(
            "/api/v1/review/",
            json={
                "product_id": test_product["product_id"],
                "text": "Great product, would buy again!",
                "rating": 5
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["product_id"] == test_product["product_id"]
        assert data["text"] == "Great product, would buy again!"
        assert data["rating"] == 5
        assert "user_id" in data
        assert "review_id" in data
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_duplicate_review(self, async_client: AsyncClient, auth_headers: dict, test_review, test_product):
        """Test attempting to create a second review for the same product by the same user"""
        response = await async_client.post(
            "/api/v1/review/",
            json={
                "product_id": test_product["product_id"],
                "text": "Another review for the same product",
                "rating": 4
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already reviewed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_review_nonexistent_product(self, async_client: AsyncClient, auth_headers: dict):
        """Test creating a review for a non-existent product"""
        nonexistent_id = str(uuid.uuid4())
        response = await async_client.post(
            "/api/v1/review/",
            json={
                "product_id": nonexistent_id,
                "text": "This product doesn't exist",
                "rating": 3
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_review_invalid_rating(self, async_client: AsyncClient, auth_headers: dict, test_product):
        """Test creating a review with an invalid rating"""
        # Test with rating below minimum
        response = await async_client.post(
            "/api/v1/review/",
            json={
                "product_id": test_product["product_id"],
                "text": "Invalid rating",
                "rating": 0
            },
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test with rating above maximum
        response = await async_client.post(
            "/api/v1/review/",
            json={
                "product_id": test_product["product_id"],
                "text": "Invalid rating",
                "rating": 6
            },
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_get_review_by_id(self, async_client: AsyncClient, auth_headers: dict, test_review):
        """Test getting a review by its ID"""
        response = await async_client.get(
            f"/api/v1/review/{test_review['review_id']}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["review_id"] == test_review["review_id"]
        assert data["product_id"] == test_review["product_id"]
        assert data["text"] == test_review["text"]
        assert data["rating"] == test_review["rating"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_review(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting a non-existent review"""
        nonexistent_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/review/{nonexistent_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_list_all_reviews(self, async_client: AsyncClient, auth_headers: dict, test_review):
        """Test listing all reviews"""
        response = await async_client.get(
            "/api/v1/review/",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1
        assert data["page"] == 1
        assert data["page_size"] >= 1
        assert data["pages"] >= 1
        
        # Check if our test review is in the response
        found = False
        for review in data["items"]:
            if review["review_id"] == test_review["review_id"]:
                found = True
                break
        assert found, "Test review not found in the response"

    @pytest.mark.asyncio
    async def test_filter_reviews_by_product(self, async_client: AsyncClient, auth_headers: dict, test_review, test_product):
        """Test filtering reviews by product ID"""
        response = await async_client.get(
            f"/api/v1/review/?product_id={test_product['product_id']}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        
        # All returned reviews should be for the specified product
        for review in data["items"]:
            assert review["product_id"] == test_product["product_id"]

    @pytest.mark.asyncio
    async def test_filter_reviews_by_rating(self, async_client: AsyncClient, auth_headers: dict, test_review, test_product):
        """Test filtering reviews by rating range"""
        # Create reviews with different ratings
        ratings = [2, 3, 4]
        for rating in ratings:
            # Create a new product for each rating to avoid duplicate review error
            product_response = await async_client.post(
                "/api/v1/product/",
                json={
                    "name": f"Test Product {rating}",
                    "price": 99.99,
                    "category_id": test_product["category_id"]
                },
                headers=auth_headers
            )
            product = product_response.json()
            
            await async_client.post(
                "/api/v1/review/",
                json={
                    "product_id": product["product_id"],
                    "text": f"Review with rating {rating}",
                    "rating": rating
                },
                headers=auth_headers
            )
        
        # Test min_rating filter
        response = await async_client.get(
            "/api/v1/review/?min_rating=4",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        for review in data["items"]:
            assert review["rating"] >= 4
        
        # Test max_rating filter
        response = await async_client.get(
            "/api/v1/review/?max_rating=3",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        for review in data["items"]:
            assert review["rating"] <= 3
        
        # Test min_rating and max_rating together
        response = await async_client.get(
            "/api/v1/review/?min_rating=3&max_rating=4",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        for review in data["items"]:
            assert 3 <= review["rating"] <= 4

    @pytest.mark.asyncio
    async def test_get_product_reviews(self, async_client: AsyncClient, auth_headers: dict, test_review, test_product):
        """Test getting reviews for a specific product"""
        response = await async_client.get(
            f"/api/v1/review/product/{test_product['product_id']}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        for review in data["items"]:
            assert review["product_id"] == test_product["product_id"]

    @pytest.mark.asyncio
    async def test_get_product_reviews_nonexistent_product(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting reviews for a non-existent product"""
        nonexistent_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/review/product/{nonexistent_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_my_reviews(self, async_client: AsyncClient, auth_headers: dict, test_review):
        """Test getting reviews created by the current user"""
        response = await async_client.get(
            "/api/v1/review/my",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        
        # Check if our test review is in the response
        found = False
        for review in data["items"]:
            if review["review_id"] == test_review["review_id"]:
                found = True
                break
        assert found, "Test review not found in the response"

    @pytest.mark.asyncio
    async def test_update_review(self, async_client: AsyncClient, auth_headers: dict, test_review):
        """Test updating a review"""
        response = await async_client.put(
            f"/api/v1/review/{test_review['review_id']}",
            json={
                "text": "Updated review text",
                "rating": 3
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["review_id"] == test_review["review_id"]
        assert data["text"] == "Updated review text"
        assert data["rating"] == 3

    @pytest.mark.asyncio
    async def test_update_nonexistent_review(self, async_client: AsyncClient, auth_headers: dict):
        """Test updating a non-existent review"""
        nonexistent_id = str(uuid.uuid4())
        response = await async_client.put(
            f"/api/v1/review/{nonexistent_id}",
            json={
                "text": "This review doesn't exist",
                "rating": 1
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_review(self, async_client: AsyncClient, auth_headers: dict, test_review):
        """Test deleting a review"""
        response = await async_client.delete(
            f"/api/v1/review/{test_review['review_id']}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify the review is no longer accessible
        response = await async_client.get(
            f"/api/v1/review/{test_review['review_id']}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_nonexistent_review(self, async_client: AsyncClient, auth_headers: dict):
        """Test deleting a non-existent review"""
        nonexistent_id = str(uuid.uuid4())
        response = await async_client.delete(
            f"/api/v1/review/{nonexistent_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_review_statistics(self, async_client: AsyncClient, auth_headers: dict, test_product):
        """Test getting review statistics for a product"""
        # Create multiple reviews for the product with different ratings
        # First, create additional test products to avoid duplicate review constraint
        ratings = [3, 4, 5, 5, 4]  # Two 5-star, two 4-star, one 3-star
        
        for i, rating in enumerate(ratings):
            product_response = await async_client.post(
                "/api/v1/product/",
                json={
                    "name": f"Stats Test Product {i}",
                    "price": 99.99,
                    "category_id": test_product["category_id"]
                },
                headers=auth_headers
            )
            product = product_response.json()
            
            await async_client.post(
                "/api/v1/review/",
                json={
                    "product_id": product["product_id"],
                    "text": f"Review with rating {rating}",
                    "rating": rating
                },
                headers=auth_headers
            )
            
            # For the last product, add multiple reviews from different users
            if i == len(ratings) - 1:
                # Store the product ID for statistics test
                stats_product_id = product["product_id"]
        
        # Get statistics for the product with multiple reviews
        response = await async_client.get(
            f"/api/v1/review/statistics/{stats_product_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "product_id" in data
        assert "average_rating" in data
        assert "total_reviews" in data
        assert "rating_counts" in data
        
        assert data["product_id"] == stats_product_id
        assert data["total_reviews"] >= 1
        
        # Check that all rating counts are included
        assert "1_star" in data["rating_counts"]
        assert "2_star" in data["rating_counts"]
        assert "3_star" in data["rating_counts"]
        assert "4_star" in data["rating_counts"]
        assert "5_star" in data["rating_counts"]

    @pytest.mark.asyncio
    async def test_review_statistics_nonexistent_product(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting review statistics for a non-existent product"""
        nonexistent_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/review/statistics/{nonexistent_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_pagination(self, async_client: AsyncClient, auth_headers: dict, test_product, test_category):
        """Test pagination functionality"""
        # Create multiple products and reviews to test pagination
        for i in range(15):
            product_response = await async_client.post(
                "/api/v1/product/",
                json={
                    "name": f"Pagination Test Product {i}",
                    "price": 99.99,
                    "category_id": test_category["category_id"]
                },
                headers=auth_headers
            )
            product = product_response.json()
            
            await async_client.post(
                "/api/v1/review/",
                json={
                    "product_id": product["product_id"],
                    "text": f"Pagination test review {i}",
                    "rating": (i % 5) + 1  # Distribute ratings 1-5
                },
                headers=auth_headers
            )
        
        # Test first page with custom page size
        response = await async_client.get(
            "/api/v1/review/?page=1&page_size=5",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) <= 5
        assert data["page"] == 1
        assert data["page_size"] == 5
        assert data["total"] >= 15
        
        # Test second page
        response = await async_client.get(
            "/api/v1/review/?page=2&page_size=5",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) <= 5
        assert data["page"] == 2
        
        # The items on page 2 should be different from page 1
        page1_response = await async_client.get(
            "/api/v1/review/?page=1&page_size=5",
            headers=auth_headers
        )
        page1_data = page1_response.json()
        
        page1_ids = [item["review_id"] for item in page1_data["items"]]
        page2_ids = [item["review_id"] for item in data["items"]]
        
        # Ensure there's no overlap between page 1 and page 2
        assert not any(id in page1_ids for id in page2_ids)
