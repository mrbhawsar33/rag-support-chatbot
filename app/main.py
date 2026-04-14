from fastapi import FastAPI
from fastapi import Depends
from fastapi.openapi.utils import get_openapi
# from fastapi import Security

from app.core.config import settings
from app.core.database import engine, Base
from app.models.user import User
from app.api import auth
from app.core.dependencies import get_current_user
from app.core.dependencies import require_role

app = FastAPI(title=settings.app_name)

# def custom_openapi():
#     if app.openapi_schema:
#         return app.openapi_schema

#     openapi_schema = get_openapi(
#         title=app.title,
#         version="1.0.0",
#         description="RAG Support Chatbot API",
#         routes=app.routes,
#     )

#     openapi_schema["components"]["securitySchemes"] = {
#         "BearerAuth": {
#             "type": "http",
#             "scheme": "bearer",
#             "bearerFormat": "JWT"
#         }
#     }

#     openapi_schema["security"] = [{"BearerAuth": []}]

#     app.openapi_schema = openapi_schema
#     return app.openapi_schema

# # Override the default OpenAPI schema generation with our custom function
# app.openapi = custom_openapi

# Database initialization
Base.metadata.create_all(bind=engine)

# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])


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