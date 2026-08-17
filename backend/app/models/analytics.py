from sqlalchemy import Column, Integer, Float, String, DateTime, func, case
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from app.core.db import Base
from typing import List, Optional
from pydantic import BaseModel

# Import your database session dependency and SQLAlchemy model
from app.core.db import get_db


class ShopperDwellLog(Base):
    __tablename__ = "shopper_dwell_logs"

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, nullable=False, index=True)
    zone_id = Column(Integer, nullable=False, index=True)
    store_name = Column(String(150), nullable=True)
    department = Column(String(150), nullable=True)
    zone_name = Column(String(150), nullable=True)
    source_mode = Column(String(50), nullable=True)   # "local_video", "webcam", "rtsp"
    enter_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    exit_timestamp = Column(DateTime(timezone=True), nullable=True)
    dwell_duration_sec = Column(Float, default=0.0)
    gaze_duration_sec = Column(Float, default=0.0)
    engagement_score = Column(Float, default=0.0)


router = APIRouter(prefix="/api/analytics", tags=["Analytics & Intelligence"])

class ZoneSummaryResponse(BaseModel):
    zone_id: int
    total_shoppers: int
    avg_dwell_sec: float
    avg_gaze_sec: float
    avg_engagement_score: float
    high_engagement_shoppers: int  # Count of shoppers with engagement_score >= 0.70

    class Config:
        from_attributes = True

@router.get("/zone-summary", response_model=List[ZoneSummaryResponse])
def get_zone_summary(db: Session = Depends(get_db)):
    results = (
        db.query(
            ShopperDwellLog.zone_id.label("zone_id"),
            func.count(ShopperDwellLog.id).label("total_shoppers"),
            func.coalesce(func.avg(ShopperDwellLog.dwell_duration_sec), 0.0).label("avg_dwell_sec"),
            func.coalesce(func.avg(ShopperDwellLog.gaze_duration_sec), 0.0).label("avg_gaze_sec"),
            func.coalesce(func.avg(ShopperDwellLog.engagement_score), 0.0).label("avg_engagement_score"),
            func.sum(
                case((ShopperDwellLog.engagement_score >= 0.70, 1), else_=0)
            ).label("high_engagement_shoppers")
        )
        .group_by(ShopperDwellLog.zone_id)
        .all()
    )

    return [
        ZoneSummaryResponse(
            zone_id=row.zone_id,
            total_shoppers=row.total_shoppers,
            avg_dwell_sec=round(float(row.avg_dwell_sec), 2),
            avg_gaze_sec=round(float(row.avg_gaze_sec), 2),
            avg_engagement_score=round(float(row.avg_engagement_score), 2),
            high_engagement_shoppers=int(row.high_engagement_shoppers or 0)
        )
        for row in results
    ]








