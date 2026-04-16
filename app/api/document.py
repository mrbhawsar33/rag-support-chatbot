from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi import Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import os
import shutil
from uuid import uuid4
from starlette.concurrency import iterate_in_threadpool
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# import threading


from app.core.database import get_db
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.document import Document
from app.models.conversation import Conversation
from app.schemas.document import DocumentResponse
from app.schemas.chat_request import ChatRequest
from app.services.embedding import get_embedding
from app.services.vector_store import get_document_collection
from app.services.document_processor import process_document_by_id
from app.services.llm import generate_answer
from app.services.rag_service import RAGService


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
        uploaded_by= current_user.user_id,
        filename=file.filename,
        file_path=file_path,
        status="uploaded"
    )

    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    # --- background processing ---
    def background_task(document_id: int):
        from app.core.database import SessionLocal
        db_session = SessionLocal()
        try:
            process_document_by_id(document_id, db_session)
        finally:
            db_session.close()

    # threading.Thread(
    #     target=background_task,
    #     args=(new_doc.document_id,)
    # ).start()

    return new_doc


@router.post("/{document_id}/process")
def process_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.user_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    result = process_document_by_id(document_id=document_id, db=db)
    return result

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


# @router.post("/chat_stream")
# def chat_stream(request: ChatRequest,
#          db: Session = Depends(get_db)
#     # , current_user = Depends(get_current_user)
#     ):

#     rag_service = RAGService(
#         chroma_client=get_document_collection(),
#         embedding_service=get_embedding,
#         llm_service=generate_answer
#     )

#     def stream_generator():
#         for token in rag_service.stream_answer(request.question):
#             yield token

#     return StreamingResponse(
#         stream_generator(),
#         media_type="text/plain"
#     )

@router.post("/chat")
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    rag_service = RAGService(
        chroma_client=get_document_collection(),
        embedding_service=get_embedding,
        llm_service=generate_answer
    )

    response = rag_service.generate_answer(request.question)

    # store conversation-----------
    # user message
    db.add(Conversation(role="user", content=request.question))

    # assistant response
    db.add(Conversation(role="assistant", content=response["answer"]))

    db.commit()

    return {
        "question": request.question,
        "answer": response["answer"],
        "sources": response["sources"],
        "metadata": response["metadata"]
    }

@router.get("/chat/history")
def get_history(db: Session = Depends(get_db)):
    conversations = db.query(Conversation).order_by(Conversation.created_at.asc()).all()

    return [
        {
            "role": c.role,
            "content": c.content
        }
        for c in conversations
    ]

@router.get("/list")
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).all()
    return [
        {
            "filename": d.filename,
            "status": d.status
        }
        for d in docs
    ]