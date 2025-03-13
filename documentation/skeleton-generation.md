# Последовательность шагов для создания скелета проекта

## 1. Настройка репозитория GitHub

### Создайте новый репозиторий на GitHub:

- Перейдите на GitHub и войдите в свой аккаунт
- Нажмите на "+" в правом верхнем углу и выберите "New repository"
- Укажите название проекта, описание и настройки приватности
- Инициализируйте репозиторий с README файлом
- Нажмите "Create repository"
### Настройте GitHub Projects для управления проектом:
- Перейдите во вкладку "Projects" в репозитории
- Нажмите "Create a project"
- Выберите шаблон (например, Kanban или Backlog)
- Настройте колонки и автоматизацию по необходимости
- Клонируйте репозиторий на локальную машину:

```bash
git clone https://github.com/ваш-юзернейм/ваш-репозиторий.git
cd ваш-репозиторий
```

## 2. Создание структуры проекта

### Создайте основные директории проекта:

```bash
mkdir -p app/api/endpoints app/core app/db app/models app/schemas app/services tests/api tests/db tests/unit
```

### Создайте файлы для настройки проекта:
```bash
touch app/__init__.py app/api/__init__.py app/api/endpoints/__init__.py
touch app/core/__init__.py app/db/__init__.py app/models/__init__.py
touch app/schemas/__init__.py app/services/__init__.py
touch app/main.py app/api/api.py app/api/deps.py
touch tests/__init__.py tests/conftest.py
touch .env .env.example .gitignore
touch requirements.txt requirements-dev.txt
touch Dockerfile docker-compose.yml
touch README.md
```

### Создайте файл настроек для проекта в app/core/config.py:
```bash
touch app/core/config.py
```

## 3. Настройка Python-окружения

### Создайте виртуальное окружение и активируйте его:
```bash
python -m venv venv
# В Linux/MacOS
source venv/bin/activate
# В Windows
venv\Scripts\activate
```

### Заполните файл requirements.txt необходимыми зависимостями:
```
fastapi>=0.95.0
uvicorn>=0.21.1
sqlalchemy>=2.0.0
alembic>=1.10.3
psycopg2-binary>=2.9.6
pydantic>=2.0.0
python-dotenv>=1.0.0
httpx>=0.24.0
```

### Заполните файл requirements-dev.txt зависимостями для разработки:

```
pytest>=7.3.1
pytest-asyncio>=0.21.0
black>=23.3.0
isort>=5.12.0
mypy>=1.2.0
flake8>=6.0.0
pre-commit>=3.2.2
```

### Установите зависимости:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

## 4. Настройка Docker и Docker Compose

### Заполните файл Dockerfile:
```docker
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Заполните файл docker-compose.yml:

```yaml
version: '3.8'

services:
    app:
    build: .
    ports:
        - "8000:8000"
    volumes:
        - ./:/app
    depends_on:
        - db
    environment:
        - DATABASE_URL=postgresql://postgres:postgres@db:5432/app_db
        - DEBUG=True

    db:
    image: postgres:15
    volumes:
        - postgres_data:/var/lib/postgresql/data
    environment:
        - POSTGRES_PASSWORD=postgres
        - POSTGRES_USER=postgres
        - POSTGRES_DB=app_db
    ports:
        - "5432:5432"

volumes:
    postgres_data:
```

## 5. Настройка FastAPI

### Настройте базовую конфигурацию в app/core/config.py:

```python
import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI App"
    PROJECT_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    DATABASE_URL: str
    
    class Config:
        env_file = ".env"
        
settings = Settings()
```

### Создайте базовое приложение FastAPI в app/main.py:
```python
from fastapi import FastAPI
from app.core.config import settings
from app.api.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    debug=settings.DEBUG
)

app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": "Welcome to the API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```
### Настройте роутеры в app/api/api.py:

```python
from fastapi import APIRouter

api_router = APIRouter()

# Здесь будет импорт и подключение эндпоинтов
# from app.api.endpoints import items, users
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(items.router, prefix="/items", tags=["items"])
```

## 6. Настройка SQLAlchemy и подключения к базе данных

### Настройте соединение с базой данных в app/db/session.py:

```python
   from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
   from sqlalchemy.orm import sessionmaker
   from app.core.config import settings

   # Преобразуем обычный URL PostgreSQL в асинхронный
   async_db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

   engine = create_async_engine(async_db_url, echo=settings.DEBUG)
   AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

   async def get_db():
       async with AsyncSessionLocal() as session:
           try:
               yield session
           finally:
               await session.close()
```

### Создайте базовую модель в app/db/base.py:
```python
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
```

## 7. Настройка Alembic для миграций

### Инициализируйте Alembic:

```bash
alembic init alembic
```

### Отредактируйте файл alembic.ini:

```python
# Файл будет создан автоматически, нужно только заменить sqlalchemy.url
sqlalchemy.url = postgresql://postgres:postgres@db:5432/app_db
```

### Настройте alembic/env.py:

```python
# В этот файл нужно добавить импорт базового класса моделей и настроек
from app.db.base import Base
from app.core.config import settings

# Заменить config.set_main_option
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Указать целевые метаданные для миграций
target_metadata = Base.metadata
```

## 8. Настройка тестирования с помощью Pytest

### Настройте tests/conftest.py:

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.main import app
from fastapi.testclient import TestClient

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"

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
```

## 9. Настройка Git-игнорирования

### Заполните файл .gitignore:

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg
venv/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Environment
.env
.venv
env/

# Docker
.docker/

# Logs
logs/
*.log

# Pytest
.pytest_cache/
.coverage
htmlcov/
```

## 10. Заполнение .env файла

### Создайте файл .env.example с примерами переменных окружения:

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/app_db
DEBUG=False
```

Создайте файл .env на основе примера и заполните его реальными значениями (не забудьте добавить его в .gitignore).


## 11. Первый коммит и пуш в репозиторий

Добавьте все файлы и сделайте первый коммит:

```bash
git add .
git commit -m "Initial project structure"
git push origin main
```

## 12. Создание базового эндпоинта для проверки работоспособности

### Создайте файл app/api/endpoints/health.py:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

router = APIRouter()

@router.get("/")
async def health_check():
    return {"status": "ok"}

@router.get("/db")
async def db_health_check(db: AsyncSession = Depends(get_db)):
    try:
        # Простой запрос для проверки подключения к БД
        await db.execute("SELECT 1")
        return {"status": "Database connection established"}
    except Exception as e:
        return {"status": "Database connection failed", "details": str(e)}
```

### Обновите app/api/api.py, чтобы включить эндпоинт проверки работоспособности:

```python
   from fastapi import APIRouter
   from app.api.endpoints import health

   api_router = APIRouter()
   api_router.include_router(health.router, prefix="/health", tags=["health"])
```

## 13. Запуск проекта

### Запустите приложение с помощью Docker Compose:

```bash
docker-compose up -d
```

Проверьте, что приложение работает, открыв в браузере:

```
   http://localhost:8000/docs
```

Проверьте эндпоинт проверки работоспособности:

```
   http://localhost:8000/health
   http://localhost:8000/health/db
```

Это базовый скелет проекта с указанными технологиями. По мере развития проекта вы можете добавлять новые модели, эндпоинты, сервисы и другие компоненты в соответствующие директории созданной структуры.