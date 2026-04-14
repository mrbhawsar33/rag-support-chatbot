from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserResponse
from app.models.user import User
from app.core.database import get_db
from app.core.security import hash_password

router = APIRouter()


@router.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):

    # Check if user already exists
    existing_user = db.query(User).filter(User.username == user.username).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_pwd = hash_password(user.password)

    new_user = User(
        username=user.username,
        password_hash=hashed_pwd,
        user_role=user.user_role
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user