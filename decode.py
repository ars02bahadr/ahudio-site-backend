
import asyncio
import sys
import hashlib
import hmac
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()

# JWT ve Password Hashing Ayarları
SECRET_KEY = "your-secret-key-change-this-in-production-123456789"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
HASH_SALT = "ahudio-salt-change-in-production-2024"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Şifreyi PBKDF2 ile doğrula"""
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        plain_password.encode('utf-8'),
        HASH_SALT.encode('utf-8'),
        100000
    )
    return hmac.compare_digest(password_hash.hex(), hashed_password)


def get_password_hash(password: str) -> str:
    """Şifreyi PBKDF2 ile hashle"""
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        HASH_SALT.encode('utf-8'),
        100000
    )
    return password_hash.hex()


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