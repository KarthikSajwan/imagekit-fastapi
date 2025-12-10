import uuid
from datetime import datetime, UTC
from sqlalchemy import Column, String, Text, DateTime
from .database import Base

class Post(Base):
    __tablename__ = "posts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    caption = Column(Text, nullable=True)
    url = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now(UTC))
