from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class DocumentResponse(BaseModel):
    document_id: int
    uploaded_by: int
    filename: str
    file_path: str
    status: str
    chunk_count: int
    processing_time: Optional[int] = None
    document_structure: Optional[str] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True