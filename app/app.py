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
# STARTUP: CREATE TABLES
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
# DATABASE DEPENDENCY
# --------------------------------------------------
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# --------------------------------------------------
# HELPER: SAFE FILE TYPE DETECTION
# --------------------------------------------------
def get_file_type(file: UploadFile) -> str:
    # 1️⃣ Try content-type (may be None)
    if file.content_type:
        if file.content_type.startswith("video/"):
            return "video"
        if file.content_type.startswith("image/"):
            return "image"

    # 2️⃣ Fallback to file extension
    ext = os.path.splitext(file.filename.lower())[1]

    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    image_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

    if ext in video_exts:
        return "video"
    if ext in image_exts:
        return "image"

    # 3️⃣ Default
    return "image"


# --------------------------------------------------
# UPLOAD FILE
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
        # Save uploaded file to temp file
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=os.path.splitext(file.filename)[1],
        ) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        # Upload to ImageKit
        with open(temp_file_path, "rb") as f:
            upload_result = imagekit.upload_file(
                file=f,
                file_name=file.filename,
                options=UploadFileRequestOptions(
                    use_unique_file_name=True,
                    tags=["backend-upload", f"user-{current_user.id}"],
                ),
            )

        if upload_result.error:
            raise HTTPException(
                status_code=500,
                detail=upload_result.error.get("message", "ImageKit upload failed"),
            )

        # Create DB post
        post = models.Post(
            caption=caption,
            url=upload_result.url,
            file_type=get_file_type(file),
            file_name=upload_result.name,
            user_id=current_user.id,
        )

        db.add(post)
        await db.commit()
        await db.refresh(post)

        return {
            "message": "Upload successful",
            "post_id": post.id,
            "file_type": post.file_type,
            "url": post.url,
        }

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

        if file and file.file:
            file.file.close()


# --------------------------------------------------
# GET USER FEED
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
# DELETE POST
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
