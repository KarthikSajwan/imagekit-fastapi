from fastapi_users import schemas
from pydantic import EmailStr
from typing import Optional


# -------------------------
# User Read (Response)
# -------------------------
class UserRead(schemas.BaseUser[str]):
    email: EmailStr
    is_active: bool
    is_superuser: bool
    is_verified: bool


# -------------------------
# User Create (Request)
# -------------------------
class UserCreate(schemas.BaseUserCreate):
    email: EmailStr
    password: str


# -------------------------
# User Update (Optional)
# -------------------------
class UserUpdate(schemas.BaseUserUpdate):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
