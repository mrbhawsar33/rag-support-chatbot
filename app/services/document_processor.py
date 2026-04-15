import os
import time

from sqlalchemy.orm import Session
# from docling.document_converter import DocumentConverter
import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_text_splitters.markdown import MarkdownHeaderTextSplitter

from app.models.document import Document
from app.services.embedding import get_embedding
from app.services.vector_store import get_document_collection


def process_document_by_id(document_id: int, db: Session):
    doc = db.query(Document).filter(Document.document_id == document_id).first()

    if not doc:
        raise ValueError("Document not found")

    start_time = time.time()
    doc.status = "processing"
    db.commit()

    try:
        # Extract markdown using Docling
        file_ext = os.path.splitext(doc.file_path)[1].lower()

        # --- handle txt separately ---
        if file_ext == ".txt":
            with open(doc.file_path, "r", encoding="utf-8") as f:
                markdown_text = f.read()

        elif file_ext == ".pdf":
            text = ""

            with pdfplumber.open(doc.file_path) as pdf:
                for page in pdf.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as e:
                        print(f"Skipping page due to error: {e}")
                        continue

            markdown_text = text

        else:
            raise ValueError("Unsupported file type for now")

        # Basic preprocessing
        cleaned_text = markdown_text.strip()

        # Split by markdown headers first
        headers_to_split_on = [
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
        ]

        header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on
        )
        header_docs = header_splitter.split_text(cleaned_text)

        # Then recursive split
        recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100
        )

        final_chunks = []
        chunk_metadatas = []

        for item in header_docs:
            split_chunks = recursive_splitter.split_text(item.page_content)

            for chunk in split_chunks:
                final_chunks.append(chunk)
                chunk_metadatas.append(item.metadata)

        # initial testing - limit to 20 chunks for now
        # final_chunks = final_chunks[:20]
        # chunk_metadatas = chunk_metadatas[:20]
        
        MAX_CHUNKS = 200  # safe upper bound

        if len(final_chunks) > MAX_CHUNKS:
            print(f"Too many chunks ({len(final_chunks)}), truncating to {MAX_CHUNKS}")
            final_chunks = final_chunks[:MAX_CHUNKS]
            chunk_metadatas = chunk_metadatas[:MAX_CHUNKS]

        # Store in Chroma
        collection = get_document_collection()

        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for i, chunk in enumerate(final_chunks):
            chunk_id = f"{doc.document_id}_{i}"
            embedding = get_embedding(chunk)

            ids.append(chunk_id)
            documents.append(chunk)
            embeddings.append(embedding)
            metadatas.append({
                "document_id": doc.document_id,
                "chunk_index": i,
                "filename": doc.filename,
                **chunk_metadatas[i]
            })

        # clear older vectors for reprocessing
        try:
            existing = collection.get(where={"document_id": doc.document_id})
            existing_ids = existing.get("ids", [])
            if existing_ids:
                collection.delete(ids=existing_ids)
        except Exception:
            pass

        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

        # Update DB
        doc.document_structure = cleaned_text[:5000]
        doc.chunk_count = len(final_chunks)
        doc.processing_time = int(time.time() - start_time)
        doc.status = "processed"
        doc.processed_at = None  # keep as-is for now if you want to set later

        db.commit()

        return {
            "document_id": doc.document_id,
            "status": doc.status,
            "chunk_count": doc.chunk_count
        }

    except Exception as e:
        doc.status = "failed"
        db.commit()
        raise e