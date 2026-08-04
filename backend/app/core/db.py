import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import DATABASE_URL

# UPDATE 'your_actual_password' and 'your_db_name' below:
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgre123@localhost:5432/retail_db"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()