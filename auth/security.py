# auth/security.py
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY             = "zmien-na-losowy-ciag-w-produkcji"
REFRESH_SECRET_KEY     = "inny-sekret-dla-refresh-tokenow"
ALGORITHM              = "HS256"
ACCESS_TOKEN_EXPIRE    = timedelta(minutes=30)
REFRESH_TOKEN_EXPIRE   = timedelta(days=7)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def _create_token(data: dict, expire_delta: timedelta, secret: str) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expire_delta
    payload["iat"] = datetime.now(timezone.utc)
    return jwt.encode(payload, secret, algorithm=ALGORITHM)

def create_access_token(data: dict) -> str:
    return _create_token(data, ACCESS_TOKEN_EXPIRE, SECRET_KEY)

def create_refresh_token(data: dict) -> str:
    return _create_token(data, REFRESH_TOKEN_EXPIRE, REFRESH_SECRET_KEY)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

def decode_refresh_token(token: str) -> dict:
    return jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])