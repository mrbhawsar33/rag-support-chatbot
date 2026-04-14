from pydantic import BaseModel
from datetime import datetime


# For user creation (request)
class UserCreate(BaseModel):
    username: str
    password: str
    user_role: str  # admin / customer


# For response (API output)
class UserResponse(BaseModel):
    user_id: int
    username: str
    user_role: str
    created_at: datetime

    class Config:
        from_attributes = True