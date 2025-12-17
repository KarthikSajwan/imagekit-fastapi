import uuid
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)

from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import User


# --------------------------------------------------
# USER DATABASE (ASYNC)
# --------------------------------------------------

async def get_user_db():
    async with AsyncSessionLocal() as session:
        yield SQLAlchemyUserDatabase(session, User)


# --------------------------------------------------
# USER MANAGER
# --------------------------------------------------

SECRET = "abcd1234"


class UserManager(BaseUserManager[User, str]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    # FastAPI-Users requires this to convert the user ID from the JWT (string)
    # into the actual ID type used by your DB model. Since your `User.id` is a
    # plain string (stored as VARCHAR), this is just the identity function.
    def parse_id(self, user_id: str) -> str:
        return user_id

    async def on_after_register(
        self,
        user: User,
        request: Optional[Request] = None,
    ):
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self,
        user: User,
        token: str,
        request: Optional[Request] = None,
    ):
        print(f"User {user.id} forgot password. Reset token: {token}")

    async def on_after_request_verify(
        self,
        user: User,
        token: str,
        request: Optional[Request] = None,
    ):
        print(f"Verification requested for user {user.id}. Token: {token}")


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


# --------------------------------------------------
# AUTH (JWT)
# --------------------------------------------------

bearer_transport = BearerTransport(
    tokenUrl="auth/jwt/login"
)


def get_jwt_strategy():
    return JWTStrategy(
        secret=SECRET,
        lifetime_seconds=60 * 60  # 1 hour
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


# --------------------------------------------------
# FASTAPI USERS INSTANCE
# --------------------------------------------------

fastapi_users = FastAPIUsers[User, str](
    get_user_manager,
    [auth_backend],
)

current_active_user = fastapi_users.current_user(active=True)
