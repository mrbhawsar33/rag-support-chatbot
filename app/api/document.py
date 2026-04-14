from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import os
import shutil
from uuid import uuid4
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.database import get_db
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.document import Document
from app.schemas.document import DocumentResponse


router = APIRouter(prefix="/api/documents", tags=["Documents"])

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

@router.post("/upload", response_model=DocumentResponse)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # RBAC
    if current_user.user_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # --- validate extension ---
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # --- validate file size ---
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    # --- generate filename ---
    unique_filename = f"{uuid4()}{file_ext}"
    file_path = os.path.join(settings.upload_dir, unique_filename)

    # --- save file ---
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # --- DB ---
    new_doc = Document(
        uploaded_by=current_user.user_id,
        filename=file.filename,
        file_path=file_path,
        status="uploaded"
    )

    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    return new_doc

@router.post("/{document_id}/process")
def process_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # RBAC
    if current_user.user_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # fetch document
    doc = db.query(Document).filter(Document.document_id == document_id).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # update status
    doc.status = "processing"
    db.commit()

    # --- basic text extraction (MVP) ---
    try:
        with open(doc.file_path, "r", encoding="utf-8") as f:
            text = f.read()

        # store raw text temporarily
        # --- chunking ---
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )

        chunks = splitter.split_text(text)

        # store chunks as simple string (MVP)
        doc.document_structure = "||CHUNK||".join(chunks[:20])  # limit for now
        doc.chunk_count = len(chunks)
        doc.status = "processed"

    except Exception as e:
        doc.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    db.commit()

    return {"message": "Document processed"}