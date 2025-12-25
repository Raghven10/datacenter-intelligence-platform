from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
import os
import secrets

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Load from environment or generate secure default
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # Generate a secure random key for development
    SECRET_KEY = secrets.token_urlsafe(32)
    print("WARNING: Using auto-generated SECRET_KEY. Set SECRET_KEY environment variable in production!")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8

def hash_password(password: str) -> str:
    
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
