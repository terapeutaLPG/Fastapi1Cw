from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from jose import JWTError

from database import get_db
from models.user import User
from schemas.user import UserCreate, UserOut
from auth.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/register", response_model=UserOut, status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=409, detail="Email jest zajety")
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=409, detail="Nazwa uzytkownika już jest zajeta")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Niepoprawna nazwa użytkownika lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "access_token":  create_access_token({"sub": str(user.id), "role": user.role}),
        "refresh_token": create_refresh_token({"sub": str(user.id)}),
        "token_type":    "bearer",
    }

@router.post("/refresh")
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_refresh_token(body.refresh_token)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Zły refresh token")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Uzytkownik nie istnieje")

    return {
        "access_token":  create_access_token({"sub": str(user.id), "role": user.role}),
        "refresh_token": create_refresh_token({"sub": str(user.id)}),
        "token_type":    "bearer",
    }