import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.base import Base, UserToken
from app.main import app
from app.db.session import get_db
from fastapi import FastAPI


TEST_DATABASE_URL = "postgresql+asyncpg://pws:pws@localhost:5432/db_pws_test"

@pytest.fixture(scope="function")
async def async_engine():
    """Create an async engine for testing."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture(scope="function")
async def async_session(async_engine):
    """Create an async session for testing."""
    async_session_maker = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session
        await session.rollback()  # Roll back any changes after the test

@pytest.fixture(scope="function")
async def override_get_db(async_session):
    """Override the get_db dependency to use the test session."""
    async def _override_get_db():
        try:
            yield async_session
        finally:
            await async_session.commit()  # Commit any changes for the test
    
    return _override_get_db

@pytest.fixture(scope="function")
async def async_client(app, override_get_db):
    """Create an async client for testing."""
    app.dependency_overrides[get_db] = override_get_db
    # For httpx AsyncClient to test against a FastAPI app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.app = app
        yield client
    app.dependency_overrides = {}

@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Create a FastAPI app instance for testing."""
    from app.main import app
    return app

@pytest.fixture(autouse=True, scope="session")
def configure_sqlalchemy_for_tests():
    for mapper in Base.registry.mappers:
        if mapper.class_ == UserToken:
            mapper.confirm_deleted_rows = False
    yield
