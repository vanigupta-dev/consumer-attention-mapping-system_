from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core import security
from app.models import models
from pydantic import BaseModel, EmailStr
from typing import cast
import bcrypt

router = APIRouter()
# In-memory fallback dictionary if database isn't attached yet
users_db = {}

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    role: str = "Store Manager"

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

@router.post("/register")
def register(user: UserRegister):
    if user.email in users_db:
        raise HTTPException(status_code=400, detail="User already registered")

    users_db[user.email] = {
        "password_hash": hash_password(user.password),
        "role": user.role
    }
    return {
        "access_token": f"token-{user.email}",
        "token_type": "bearer",
        "email": user.email,
        "role": user.role
    }

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_db.get(form_data.username)

    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    return {
        "access_token": f"token-{form_data.username}",
        "token_type": "bearer",
        "role": user["role"]
    }