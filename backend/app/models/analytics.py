from sqlalchemy import Column, Integer, Float, String, DateTime, func
from app.core.db import Base


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