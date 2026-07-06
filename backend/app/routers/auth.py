from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models import models
from app.core import security

router = APIRouter(prefix="/auth", tags=["User Authentication"])

@router.post("/register")
def register_user(email: str, password: str, role: str = "Store Manager", db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = security.hash_password(password)
    new_user = models.User(email=email, hashed_password=hashed, role=role)
    db.add(new_user)
    db.commit()
    return {"status": "User created safely", "email": email}

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()

    # By checking 'not user' first, we confirm 'user' exists.
    # Then we explicitly cast or verify the password attribute as a clean string.
    if not user or not security.verify_password(form_data.password, str(user.hashed_password)):
        raise HTTPException(status_code=400, detail="Incorrect credentials")

    token = security.create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}