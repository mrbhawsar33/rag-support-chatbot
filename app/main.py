from fastapi import FastAPI
from fastapi import Depends
from fastapi.openapi.utils import get_openapi
# from fastapi import Security

from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth
from app.api.document import router as document_router
from app.core.dependencies import get_current_user
from app.core.dependencies import require_role


# SQLAlchemy models
from app.models.user import User
from app.models.document import Document

app = FastAPI(title=settings.app_name)

# Database initialization
Base.metadata.create_all(bind=engine)

# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(document_router)

@app.get("/")
def read_root():
    return {
        "message": f"{settings.app_name} is running"
    }

@app.get("/protected")
def protected_route(user: dict = Depends(get_current_user)):
    print("USER INSIDE ROUTE:", user) 
    return {
        "message": "You are authenticated",
        "user": user
    }

@app.get("/admin-only")
def admin_route(user=Depends(require_role("admin"))):
    return {
        "message": "Welcome Admin",
        "user": user
    }

