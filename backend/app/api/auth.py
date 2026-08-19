from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.core.db import get_db

router = APIRouter()

class LoginSchema(BaseModel):
    email: EmailStr
    password: str

class RegisterSchema(BaseModel):
    email: EmailStr
    password: str
    role: str = "Store Manager"

@router.post("/login")
def login(credentials: LoginSchema, db: Session = Depends(get_db)):
    email = credentials.email
    password = credentials.password

    # TODO: Verify email/password against your database model here
    # Example placeholder response:
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    return {
        "status": "success",
        "user": {
            "email": email,
            "role": "Store Manager" # Return actual user role from DB
        },
        "token": "fake-jwt-token"
    }

@router.post("/register")
def register(data: RegisterSchema, db: Session = Depends(get_db)):
    # TODO: Create new user in DB
    return {"status": "success", "user": {"email": data.email, "role": data.role}}