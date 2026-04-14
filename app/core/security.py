from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
import hashlib

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    print("RAW PASSWORD LENGTH:", len(password))  # DEBUG

    password = password[:72]

    sha256_hash = hashlib.sha256(password.encode()).hexdigest()

    print("AFTER SHA256 LENGTH:", len(sha256_hash))  # DEBUG

    return pwd_context.hash(sha256_hash)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    plain_password = plain_password[:72]
    sha256_hash = hashlib.sha256(plain_password.encode()).hexdigest()
    return pwd_context.verify(sha256_hash, hashed_password)