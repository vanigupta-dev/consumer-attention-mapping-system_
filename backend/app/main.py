import os
from fastapi import FastAPI, HTTPException, Depends, Response
from pydantic import BaseModel
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from fastapi.responses import Response

from app.models.analytics import ShopperDwellLog
from app.models import analytics
from app.services.video import ThreadedVideoIngest, SOURCE_TO_ZONE_ID
from app.core.db import engine, Base, get_db
from app.api import auth, store


LOCAL_VIDEO_LIBRARY = {
    "electronics": "app/assets/electronics_display.mp4",
    "grocery": "app/assets/grocery_dwell.mp4",
    "apparel": "app/assets/apparel_checkout.mp4",
}

FALLBACK_VIDEO = LOCAL_VIDEO_LIBRARY["grocery"]


@asynccontextmanager
async def lifespan_context(app: FastAPI):
    print("[STARTUP] Syncing Database Layout with PostgreSQL...")

    # WHY import analytics explicitly here: SQLAlchemy's Base.metadata only
    # knows about models that have been imported into memory at least once.
    # If ShopperDwellLog was never imported anywhere before create_all runs,
    # its table never gets created and every INSERT silently fails.

    Base.metadata.create_all(bind=engine)
    print("[STARTUP] Tables synced (including shopper_dwell_logs)")

    user_choice = os.getenv("VIDEO_SOURCE_CHOICE", "B").strip().upper()
    print("=" * 50)
    print(f"[SYSTEM] Initializing Media Stream Ingestion Engine: Mode {user_choice}")

    if user_choice == "A":
        video_source = "0"
        zone_id = 201
        print("[CONFIG] Profile A Active: Hardware Integrated Web Camera")
    elif user_choice == "B":
        file_choice = os.getenv("VIDEO_FILE_CHOICE", "grocery").strip().lower()
        video_source = LOCAL_VIDEO_LIBRARY.get(file_choice, LOCAL_VIDEO_LIBRARY["grocery"])
        zone_id = SOURCE_TO_ZONE_ID.get(file_choice, 102)
        print(f"[CONFIG] Profile B Active: {video_source}")
    elif user_choice == "C":
        video_source = os.getenv(
            "RTSP_URL", "rtsp://admin:password@192.168.1.100:554/stream1"
        )
        zone_id = 301
        print("[CONFIG] Profile C Active: Commercial CCTV Low-Latency Network Stream")
    else:
        print(f"[ERROR] '{user_choice}' invalid. Defaulting to Profile B.")
        video_source = LOCAL_VIDEO_LIBRARY["grocery"]
        zone_id = 102

    print("=" * 50)

    app.state.video_stream = ThreadedVideoIngest(
        source=video_source,
        fallback_source=FALLBACK_VIDEO,
        zone_id=zone_id
    )
    app.state.video_stream.start_processing()

    yield

    print("[SHUTDOWN] Safely unlinking background media streams...")
    app.state.video_stream.stop_processing()


description = """
### Retail Computer Vision & Attention Mapping Engine

This system ingests video feeds (Webcam, RTSP, Local Assets), tracks shoppers
with **YOLOv8**, detects gaze via **MediaPipe FaceLandmarker**, and automatically
logs dwell time and engagement scores to PostgreSQL as real interactions occur.

---

### Quick Navigation
* **Live Stream with Overlays:** [Open Stream](http://127.0.0.1:8000/api/video/stream)
* **Live Stream Metadata:** [Video Status](http://127.0.0.1:8000/api/video/status)
* **Saved Dwell Logs:** [Analytics](http://127.0.0.1:8000/api/analytics/dwell-logs)

---

### How to Switch Sources (`POST /api/video/source`)
* **Webcam:** `{"mode": "webcam"}`
* **Grocery:** `{"mode": "local", "local_choice": "grocery"}`
* **Electronics:** `{"mode": "local", "local_choice": "electronics"}`
* **Apparel:** `{"mode": "local", "local_choice": "apparel"}`
* **RTSP:** `{"mode": "rtsp", "rtsp_url": "rtsp://192.168.1.x:8080/h264_ulaw.sdp"}`

Logs appear in `GET /api/analytics/dwell-logs` after a shopper **exits the zone**
or the local video loops. Watch terminal for `[DB LOG]` lines.
"""

app = FastAPI(
    title="Consumer Attention Mapping System",
    description=description,
    version="3.1.0"
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(store.router, prefix="/api/store", tags=["Store Analytics"])
app.include_router(analytics.router)

@app.get("/api/analytics/dwell-logs", tags=["Analytics & Intelligence"])
def get_recent_dwell_logs(
    response: Response,
    limit: int = 20,
    zone_id: int | None = None,
    source_mode: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Returns real dwell logs written by the YOLO+MediaPipe pipeline.
    Logs are written when a tracked person exits the zone (or video loops).

    Filter options:
    - zone_id: 101=electronics, 102=grocery, 103=apparel, 201=webcam, 301=rtsp
    - source_mode: local_video | webcam | rtsp
    """
    response.headers["Cache-Control"] = "no-store"
    query = db.query(ShopperDwellLog).order_by(ShopperDwellLog.id.desc())
    if zone_id is not None:
        query = query.filter(ShopperDwellLog.zone_id == zone_id)
    if source_mode is not None:
        query = query.filter(ShopperDwellLog.source_mode == source_mode)
    logs = query.limit(limit).all()

    return {
        "status": "success",
        "count": len(logs),
        "filters_applied": {
            "zone_id": zone_id,
            "source_mode": source_mode
        },
        "hint": (
            "Logs appear after a shopper exits the zone or the local "
            "video loops. Watch the terminal for [DB LOG] lines."
        ),
        "data": [
            {
                "id": log.id,
                "track_id": log.track_id,
                "zone_id": log.zone_id,
                "store_name": log.store_name,
                "department": log.department,
                "zone_name": log.zone_name,
                "source_mode": log.source_mode,
                "enter_timestamp": str(log.enter_timestamp),
                "dwell_duration_sec": log.dwell_duration_sec,
                "gaze_duration_sec": log.gaze_duration_sec,
                "engagement_score": log.engagement_score,
            }
            for log in logs
        ]
    }


class VideoSourceRequest(BaseModel):
    mode: str
    local_choice: str | None = None
    rtsp_url: str | None = None


@app.post("/api/video/source", tags=["Video Stream Control"])
def switch_video_source(data: VideoSourceRequest):
    global FALLBACK_VIDEO

    if data.mode == "webcam":
        new_source = "0"
        zone_id = 201
        description_text = "Hardware Integrated Web Camera"

    elif data.mode == "local":
        if data.local_choice not in LOCAL_VIDEO_LIBRARY:
            raise HTTPException(
                status_code=400,
                detail=f"local_choice must be one of {list(LOCAL_VIDEO_LIBRARY.keys())}"
            )
        new_source = LOCAL_VIDEO_LIBRARY[data.local_choice]
        zone_id = SOURCE_TO_ZONE_ID.get(data.local_choice, 102)
        description_text = f"Local video: {data.local_choice}"
        FALLBACK_VIDEO = new_source

    elif data.mode == "rtsp":
        if not data.rtsp_url:
            raise HTTPException(
                status_code=400,
                detail="rtsp_url is required when mode='rtsp'"
            )
        new_source = data.rtsp_url
        zone_id = 301
        description_text = "RTSP live stream"

    else:
        raise HTTPException(
            status_code=400,
            detail="mode must be 'webcam', 'local', or 'rtsp'"
        )

    print(f"[VIDEO] Switching -> {description_text} ({new_source}) [Zone:{zone_id}]")
    app.state.video_stream.stop_processing()
    app.state.video_stream = ThreadedVideoIngest(
        source=new_source,
        fallback_source=FALLBACK_VIDEO,
        zone_id=zone_id
    )
    app.state.video_stream.start_processing()

    return {
        "status": "switched",
        "description": description_text,
        "source": new_source,
        "zone_id": zone_id,
        "active_fallback": FALLBACK_VIDEO
    }


@app.get("/api/video/status", tags=["Video Stream Control"])
def video_status(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {
        "available_local_videos": list(LOCAL_VIDEO_LIBRARY.keys()),
        "metadata": app.state.video_stream.get_latest_metadata(),
    }


@app.get("/api/video/stream", tags=["Video Stream Control"])
def get_video_stream(response: Response):
    response.headers["Cache-Control"] = "no-store"
    if not hasattr(app.state, "video_stream") or app.state.video_stream is None:
        raise HTTPException(status_code=503, detail="Video engine not initialized")
    jpeg_bytes = app.state.video_stream.get_latest_jpeg()
    if not jpeg_bytes:
        raise HTTPException(
            status_code=503,
            detail="Frame buffer warming up, try again in a moment"
        )
    return Response(content=jpeg_bytes, media_type="image/jpeg")


@app.get("/")
def home(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {
        "status": "Attention Mapping System Active",
        "active_profile": os.getenv("VIDEO_SOURCE_CHOICE", "B").upper(),
        "docs": "http://127.0.0.1:8000/docs",
        "stream": "http://127.0.0.1:8000/api/video/stream",
        "analytics": "http://127.0.0.1:8000/api/analytics/dwell-logs"
    }