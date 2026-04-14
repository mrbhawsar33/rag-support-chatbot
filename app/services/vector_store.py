import chromadb
from chromadb.config import Settings

from app.core.config import settings


def get_chroma_client():
    return chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
        settings=Settings(
            anonymized_telemetry=False
        )
    )


def get_document_collection():
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=settings.chroma_collection_name
    )
    return collection