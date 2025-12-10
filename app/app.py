from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Form
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models

from app.images import imagekit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions

import shutil
import os
import tempfile


app = FastAPI()

# Create DB tables
models.Base.metadata.create_all(bind=engine)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------------
#                UPLOAD ENDPOINT
# --------------------------------------------------------
@app.post("/upload")
def upload_file(
    file: UploadFile = File(...),
    caption: str = Form(""),
    db: Session = Depends(get_db)
):
    temp_file_path = None

    try:
        # -----------------------------------------
        # Save file temporarily
        # -----------------------------------------
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        # -----------------------------------------
        # Upload to ImageKit
        # -----------------------------------------
        upload_result = imagekit.upload_file(
            file=open(temp_file_path, "rb"),
            file_name=file.filename,
            options=UploadFileRequestOptions(
                use_unique_file_name=True,
                tags=["backend-upload"]
            )
        )

        if upload_result.response.http_status_code != 200:
            raise HTTPException(status_code=500, detail="ImageKit upload failed")

        # -----------------------------------------
        # Determine file type (image or video)
        # -----------------------------------------
        file_type = "video" if file.content_type.startswith("video/") else "image"

        # -----------------------------------------
        # Save metadata into DB
        # -----------------------------------------
        post = models.Post(
            caption=caption,
            url=upload_result.url,
            file_type=file_type,
            file_name=upload_result.name,
        )

        db.add(post)
        db.commit()
        db.refresh(post)

        return {
            "message": "Upload successful",
            "post": post
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Delete temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

        file.file.close()


# --------------------------------------------------------
#                     FEED ENDPOINT
# --------------------------------------------------------
@app.get("/feed")
def get_feed(db: Session = Depends(get_db)):
    posts = db.query(models.Post).order_by(models.Post.created_at.desc()).all()

    posts_data = [
        {
            "id": str(post.id),
            "caption": post.caption,
            "url": post.url,
            "file_type": post.file_type,
            "file_name": post.file_name,
            "created_at": post.created_at.isoformat() if post.created_at else None
        }
        for post in posts
    ]

    return {"posts": posts_data}
