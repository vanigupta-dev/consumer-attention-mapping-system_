from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import RoleChecker
from app.models import models
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()
require_manager = RoleChecker(["SuperAdmin", "StoreManager"])

class ZoneSchema(BaseModel):
    zone_id: int
    name: str
    coordinates: List[List[int]]

class ShelfCreateSchema(BaseModel):
    shelf_name: str
    zones: List[ZoneSchema]

class StoreCreateSchema(BaseModel):
    name: str
    location: str

@router.get("/stores")
def get_stores(db: Session = Depends(get_db)):
    return db.query(models.Store).all()

@router.post("/stores", dependencies=[Depends(require_manager)])
def create_store(store_data: StoreCreateSchema, db: Session = Depends(get_db)):
    new_store = models.Store(name=store_data.name, location=store_data.location)
    db.add(new_store)
    db.commit()
    db.refresh(new_store)
    return new_store

@router.get("/stores/{store_id}/shelves")
def get_shelves(store_id: str, db: Session = Depends(get_db)):
    return db.query(models.Shelf).filter(models.Shelf.store_id == store_id).all()

@router.post("/stores/{store_id}/shelves", dependencies=[Depends(require_manager)])
def create_shelf(store_id: str, shelf_data: ShelfCreateSchema, db: Session = Depends(get_db)):
    store = db.query(models.Store).filter(models.Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Target Retail Store instance not found")

    zones_json = [zone.dict() for zone in shelf_data.zones]
    new_shelf = models.Shelf(store_id=store_id, shelf_name=shelf_data.shelf_name, zones=zones_json)
    db.add(new_shelf)
    db.commit()
    db.refresh(new_shelf)
    return {"layout_id": new_shelf.id, "name": new_shelf.shelf_name, "zones": new_shelf.zones}