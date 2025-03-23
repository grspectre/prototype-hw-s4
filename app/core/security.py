import hashlib
import random
import string
import datetime
from uuid import uuid4
from app.db.base import User, UserToken
from fastapi import Depends, Security, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from app.db.session import get_db
from sqlalchemy import select

http_bearer = HTTPBearer()

async def get_token(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials = Security(http_bearer)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    query = select(UserToken).filter(UserToken.token_id == credentials.credentials)
    response = await db.execute(query)
    token = response.scalar_one_or_none()
    if token is None:
        raise credentials_exception        
    return token


async def get_token_if_not_expired(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials = Security(http_bearer)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    query = select(UserToken).filter(UserToken.token_id == credentials.credentials)
    response = await db.execute(query)
    token = response.scalar_one_or_none()
    if token is None or token.is_expired():
        raise credentials_exception        
    return token


def get_hash(pwd: str, salt: str) -> str:
    return hashlib.md5(f"{pwd}{salt}".encode("utf8")).hexdigest()


def create_access_token(data, expires_delta):
    return (uuid4(), datetime.datetime.now() + expires_delta)


def get_password_hash(pwd: str):
    salt = ''.join(random.choices(string.digits + 'abcdef', k=32))
    return get_hash(pwd,  salt), salt


def verify_password(password: str, hash: str, salt: str):
    return hash == get_hash(password, salt)
