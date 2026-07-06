from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pymongo import MongoClient

# 1. FIX: Make sure this uses mysql+pymysql and port 3306!
MYSQL_URL = "mysql+pymysql://root:12345@localhost:3306/retail_db"
MONGO_URL = "mongodb://localhost:27017/"

# 2. FIX: Ensure the engine is explicitly binding the MYSQL_URL
engine = create_engine(MYSQL_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

mongo_client = MongoClient(MONGO_URL)
mongo_db = mongo_client["retail_metadata"]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()