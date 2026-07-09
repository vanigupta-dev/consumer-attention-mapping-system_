from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core import security
from app.models import models
from pydantic import BaseModel, EmailStr
from typing import cast

router = APIRouter()

class UserRegisterSchema(BaseModel):
    email: EmailStr
    password: str
    role: str = "StoreManager"

@router.post("/register")
def register(user_data: UserRegisterSchema, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Account already registered under this email")

    hashed = security.hash_password(user_data.password)
    new_user = models.User(email=user_data.email, hashed_password=hashed, role=user_data.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "email": new_user.email, "role": new_user.role, "is_active": True}

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    # ensure user and hashed_password exist before calling verify_password
    if user is None or getattr(user, "hashed_password", None) is None or not security.verify_password(form_data.password, cast(str, getattr(user, "hashed_password"))):
        raise HTTPException(status_code=401, detail="Invalid credential validation profiles")

    token = security.create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}