from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi import Query
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
from app.services.embedding import get_embedding
from app.services.vector_store import get_document_collection


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

        # --- chunking ---
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )

        chunks = splitter.split_text(text)

        # limit for MVP
        chunks = chunks[:20]

        collection = get_document_collection()

        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc.document_id}_{i}"

            embedding = get_embedding(chunk)

            ids.append(chunk_id)
            documents.append(chunk)
            embeddings.append(embedding)
            metadatas.append({
                "document_id": doc.document_id,
                "chunk_index": i,
                "filename": doc.filename
            })

        # store in Chroma
        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

        # update DB
        doc.chunk_count = len(chunks)
        doc.status = "processed"

        db.commit()

    except Exception as e:
        doc.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    db.commit()

    return {"message": "Document processed"}

@router.get("/search")
def search_documents(
    query: str = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # no RBAC restriction for now (customer can use)
    # embed query
    query_embedding = get_embedding(query)

    # get collection
    collection = get_document_collection()

    # search
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5
    )

    return {
        "query": query,
        "results": results
    }

@router.post("/chat")
def chat(
    query: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    from app.services.embedding import get_embedding
    from app.services.vector_store import get_document_collection
    from app.services.llm import generate_answer

    # embed query
    query_embedding = get_embedding(query)

    # retrieve
    collection = get_document_collection()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5
    )

    chunks = results.get("documents", [[]])[0]

    # build context
    context = "\n\n".join(chunks)

    # prompt
    prompt = f"""
You are a helpful support assistant.

Answer ONLY using the context below.
If answer is not present, say: "I don't know."

CONTEXT:
{context}

QUESTION:
{query}

ANSWER:
"""

    # generate
    answer = generate_answer(prompt)

    return {
        "question": query,
        "answer": answer,
        "sources": chunks
    }