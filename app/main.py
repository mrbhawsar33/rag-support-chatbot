from fastapi import FastAPI
from app.core.config import settings
from app.core.database import engine, Base
from app.models.user import User
from app.api import auth

app = FastAPI(title=settings.app_name)

# Database initialization
Base.metadata.create_all(bind=engine)

# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])


@app.get("/")
def read_root():
    return {
        "message": f"{settings.app_name} is running"
    }