import uuid
from sqlalchemy import Column, String, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship
from app.core.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="StoreManager")  # SuperAdmin, StoreManager, Analyst

class Store(Base):
    __tablename__ = "stores"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)

    shelves = relationship("Shelf", back_populates="store", cascade="all, delete-orphan")

class Shelf(Base):
    __tablename__ = "shelves"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False)
    shelf_name = Column(String(255), nullable=False)
    zones = Column(JSON, nullable=True)  # Follows contract: [{"zone_id": 1, "name": "Aisle 3", "coordinates": [[x1, y1], [x2, y2]]}]

    store = relationship("Store", back_populates="shelves")