
import asyncio
import sys
import hashlib
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# JWT ve Password Hashing Ayarları
SECRET_KEY = "your-secret-key-change-this-in-production-123456789"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def verify_password(plain_password, hashed_password):
    # Uzun şifreleri SHA256 ile hash'leyip 72 byte limitine uy
    if len(plain_password.encode('utf-8')) > 72:
        plain_password = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    # Uzun şifreleri SHA256 ile hash'leyip 72 byte limitine uy
    if len(password.encode('utf-8')) > 72:
        password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    JWT token doğrulama fonksiyonu
    Authorization header'ında Bearer token olması gerekiyor
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token geçersiz")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Token doğrulanamadı")