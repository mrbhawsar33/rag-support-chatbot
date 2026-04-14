from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime, timezone

from app.core.database import Base


class Document(Base):
    __tablename__ = "document"

    document_id = Column(Integer, primary_key=True, index=True)
    uploaded_by = Column(Integer, ForeignKey("user.user_id"), nullable=False)
    # parent_doc_id = Column(Integer, nullable=True)  # For chunked documents
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False, unique=True)
    status = Column(String, nullable=False, default="uploaded")
    chunk_count = Column(Integer, default=0)
    processing_time = Column(Integer, nullable=True)  # Time taken to process document in seconds
    document_structure = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime, nullable=True)