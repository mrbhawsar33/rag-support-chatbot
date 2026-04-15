from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.document import Document
from app.services.document_processor import process_document_by_id


def process_pending_documents():
    db: Session = SessionLocal()

    try:
        # docs = db.query(Document).filter(Document.status == "uploaded").all()
        doc = db.query(Document).filter(Document.status == "uploaded").first()

        # for doc in docs:
        if doc:
            try:
                process_document_by_id(doc.document_id, db)
            except Exception as e:
                print(f"Failed processing document {doc.document_id}: {e}")

    finally:
        db.close()


scheduler = BackgroundScheduler()


def start_scheduler():
    scheduler.add_job(
        process_pending_documents,
        "interval",
        seconds=30,  # every 30 seconds
        max_instances=1  # prevent overlapping runs
    )
    scheduler.start()