import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from app.services.video import ThreadedVideoIngest, SOURCE_TO_ZONE_ID
from app.core.db import engine, Base
from app.api import auth, store
from fastapi.responses import Response, StreamingResponse

LOCAL_VIDEO_LIBRARY = {
    "electronics": "app/assets/electronics_display.mp4",
    "grocery": "app/assets/grocery_dwell.mp4",
    "apparel": "app/assets/apparel_checkout.mp4",
}

FALLBACK_VIDEO = LOCAL_VIDEO_LIBRARY["grocery"]

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[STARTUP] Syncing Database Layout with PostgreSQL...")
    Base.metadata.create_all(bind=engine)

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
        print(f"[CONFIG] Profile B Active: Localized Professional Stock Media ({video_source})")
    elif user_choice == "C":
        video_source = os.getenv("RTSP_URL", "rtsp://admin:password@192.168.1.100:554/stream1")
        zone_id = 301
        print("[CONFIG] Profile C Active: Commercial CCTV Low-Latency Network Stream")
    else:
        print(f"[ERROR] Signature '{user_choice}' recognized as invalid. Defaulting to Profile B.")
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

Welcome to the backend management console. This system ingests multi-source video feeds (Webcam, RTSP, Local Assets), extracts facial landmarks via **MediaPipe Face Mesh**, tracks objects using **YOLOv8**, and calculates head pose metrics.

---

###  Quick Navigation Links
* **Live Visual Stream with Overlays:** [Open Stream Buffer](http://127.0.0.1:8000/api/video/stream)
* **Live Stream JSON Metadata:** [Inspect Video Status](http://127.0.0.1:8000/api/video/status)


---

###  How to Test Source Switching (`POST /api/video/source`)
1. Expand the `POST /api/video/source` section below.
2. Click **Try it out**.
3. Use one of these JSON payloads:
 * **Webcam Mode:** `{"mode": "webcam"}`
 * **Local Video Mode:** `{"mode": "local", "local_choice": "electronics"}`
 * **RTSP Mode:** `{"mode": "rtsp", "rtsp_url":"http://172.25.234.154:8080/video"}`
"""

app = FastAPI(
    title="Consumer Attention Mapping System",
    description=description,
    version="3.0.0",
    lifespan=lifespan)
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(store.router, prefix="/api/store", tags=["Store Analytics"])


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
        description = "Hardware Integrated Web Camera"
    elif data.mode == "local":
        if data.local_choice not in LOCAL_VIDEO_LIBRARY:
            raise HTTPException(status_code=400, detail=f"local_choice must be one of {list(LOCAL_VIDEO_LIBRARY.keys())}")
        new_source = LOCAL_VIDEO_LIBRARY[data.local_choice]
        zone_id = SOURCE_TO_ZONE_ID.get(data.local_choice, 102)
        description = f"Local video: {data.local_choice}"
        FALLBACK_VIDEO = new_source
    elif data.mode == "rtsp":
        if not data.rtsp_url:
            raise HTTPException(status_code=400, detail="rtsp_url is required when mode='rtsp'")
        new_source = data.rtsp_url
        zone_id = 301
        description = "RTSP live stream"
    else:
        raise HTTPException(status_code=400, detail="mode must be 'webcam', 'local', or 'rtsp'")

    print(f"[VIDEO] Switching source -> {description} ({new_source}) [Zone ID: {zone_id}]")
    app.state.video_stream.stop_processing()
    app.state.video_stream = ThreadedVideoIngest(
        source=new_source,
        fallback_source=FALLBACK_VIDEO,
        zone_id=zone_id
    )
    app.state.video_stream.start_processing()
    return {
        "status": "switched",
        "description": description,
        "source": new_source,
        "zone_id": zone_id,
        "active_fallback": FALLBACK_VIDEO
    }

@app.get("/api/video/status", tags=["Video Stream Control"])
def video_status():
     return {
            "available_local_videos": list(LOCAL_VIDEO_LIBRARY.keys()),
            "metadata": app.state.video_stream.get_latest_metadata(),
        }

@app.get("/api/video/stream", tags=["Video Stream Control"])
def get_video_stream():
    """
    Returns the latest processed frame from the active video ingest thread.
    Includes YOLO bounding boxes and MediaPipe Face Mesh annotations.
    """
    if not hasattr(app.state, "video_stream") or app.state.video_stream is None:
        raise HTTPException(status_code=503, detail="Video engine not initialized")

    jpeg_bytes = app.state.video_stream.get_latest_jpeg()
    if not jpeg_bytes:
        raise HTTPException(status_code=503, detail="Frame buffer is warming up")

    return Response(content=jpeg_bytes, media_type="image/jpeg")
