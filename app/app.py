from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import AsyncSessionLocal, engine
from app import models
from app.models import User

from app.users import fastapi_users, auth_backend, current_active_user
from app.schemas import UserRead, UserCreate

from app.images import imagekit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions

import shutil
import os
import tempfile


app = FastAPI()


# --------------------------------------------------
# CREATE TABLES (ASYNC)
# --------------------------------------------------

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)


# --------------------------------------------------
# AUTH ROUTES
# --------------------------------------------------

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)


# --------------------------------------------------
# DB DEPENDENCY (ASYNC)
# --------------------------------------------------

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# --------------------------------------------------
# UPLOAD (PROTECTED)
# --------------------------------------------------

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    caption: str = Form(""),
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    temp_file_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=os.path.splitext(file.filename)[1],
        ) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        with open(temp_file_path, "rb") as f:
            upload_result = imagekit.upload_file(
                file=f,
                file_name=file.filename,
                options=UploadFileRequestOptions(
                    use_unique_file_name=True,
                    tags=["backend-upload"],
                ),
            )

        if upload_result.error:
            raise HTTPException(
                status_code=500,
                detail=upload_result.error.get("message", "ImageKit upload failed"),
            )

        post = models.Post(
            caption=caption,
            url=upload_result.url,
            file_type="video" if file.content_type.startswith("video/") else "image",
            file_name=upload_result.name,
            user_id=current_user.id,
        )

        db.add(post)
        await db.commit()
        await db.refresh(post)

        return {"message": "Upload successful", "post_id": post.id}

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        file.file.close()


# --------------------------------------------------
# FEED (PROTECTED)
# --------------------------------------------------

@app.get("/feed")
async def get_feed(
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(models.Post)
        .where(models.Post.user_id == current_user.id)
        .order_by(models.Post.created_at.desc())
    )

    result = await db.execute(stmt)
    posts = result.scalars().all()

    return {"posts": posts}


# --------------------------------------------------
# DELETE (PROTECTED)
# --------------------------------------------------

@app.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(models.Post).where(
        models.Post.id == post_id,
        models.Post.user_id == current_user.id,
    )

    result = await db.execute(stmt)
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    await db.delete(post)
    await db.commit()

    return {"message": "Post deleted"}
