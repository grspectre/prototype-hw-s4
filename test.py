from app.core.security import create_access_token
from app.db.base import UserRoles, UserToken
from sqlalchemy import select
from datetime import timedelta
from uuid import uuid4
roles = [UserRoles.user]
from app.db.session import get_db
import asyncio

ACCESS_TOKEN_EXPIRE_MINUTES = 30

async def main():
    it = get_db()
    session = await it.__anext__()

    # Create access token
    query = select(UserToken).filter(UserToken.token_id == r"b5d4f789-58ef-420b-8b78-569260d2bdb1")
    response = await session.execute(query)
    token = response.scalar_one()
    print(token.is_expired())

asyncio.run(main())
