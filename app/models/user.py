from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timezone

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    user_role = Column(String, nullable=False)  # admin / customer
    created_at = Column(DateTime, default=datetime.now(timezone.utc))