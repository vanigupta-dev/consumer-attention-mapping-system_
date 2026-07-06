from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models import models
from app.core.security import verify_role

router = APIRouter(prefix="/stores", tags=["Store & Shelf Management"])

@router.post("/")
def create_store(name: str, location: str, db: Session = Depends(get_db), current_user: dict = Depends(verify_role(["Admin"]))):
    new_store = models.Store(name=name, location=location)
    db.add(new_store)
    db.commit()
    db.refresh(new_store)
    return {"store_id": new_store.id, "name": new_store.name}

@router.post("/{store_id}/shelves")
def map_shelf(store_id: int, zone_name: str, x_min: int, y_min: int, x_max: int, y_max: int, db: Session = Depends(get_db), current_user: dict = Depends(verify_role(["Admin", "Store Manager"]))):
    if not db.query(models.Store).filter(models.Store.id == store_id).first():
        raise HTTPException(status_code=404, detail="Target Store facility not found")
    new_shelf = models.Shelf(store_id=store_id, zone_name=zone_name, x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max)
    db.add(new_shelf)
    db.commit()
    db.refresh(new_shelf)
    return {"status": "success", "shelf_id": new_shelf.id}