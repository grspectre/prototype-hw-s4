# conftest.py
import pytest

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.main import app
from fastapi.testclient import TestClient
from app.db.session import get_db

TEST_DATABASE_URL = "postgresql+asyncpg://pws:pws@localhost:5432/db_pws_test"


@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
async def async_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def async_session(async_engine):
    async_session_maker = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session

@pytest.fixture
def override_get_db(async_session):
    async def _override_get_db():
        try:
            yield async_session
        finally:
            pass
    
    return _override_get_db

@pytest.fixture
def client_with_db(client, override_get_db):
    app.dependency_overrides[get_db] = override_get_db
    yield client
    app.dependency_overrides = {}