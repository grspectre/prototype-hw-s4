import pytest
from app.main import app
from app.db.session import get_db


def test_health_check(client):
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_db_health_check(client):
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json()["status"] == "Database connection established"


@pytest.mark.asyncio
async def test_db_health_check_failure(client, monkeypatch):
    # Mock the database query to raise an exception
    from sqlalchemy.ext.asyncio import AsyncSession
    
    original_execute = AsyncSession.execute
    
    async def mock_execute(*args, **kwargs):
        raise Exception("Database connection error")
    
    monkeypatch.setattr(AsyncSession, "execute", mock_execute)
    

    # Apply override to force using our mocked session
    async def mock_get_db():
        try:
            session = AsyncSession()
            yield session
        finally:
            await session.close()
    
    app.dependency_overrides[get_db] = mock_get_db
    
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json()["status"] == "Database connection failed"
    assert "details" in response.json()
    
    # Clean up
    app.dependency_overrides = {}
    monkeypatch.setattr(AsyncSession, "execute", original_execute)