import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.services.video import ThreadedVideoIngest
from app.core.db import engine, Base

#  1. IMPORT YOUR ROUTERS HERE
from app.api import auth, store

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[STARTUP] Syncing Database Layout with PostgreSQL...")
    Base.metadata.create_all(bind=engine)

    user_choice = os.getenv("VIDEO_SOURCE_CHOICE", "B").strip().upper()

    print("=" * 50)
    print(f"[SYSTEM] Initializing Media Stream Ingestion Engine: Mode {user_choice}")

    if user_choice == "A":
        video_source = "0"
        print("[CONFIG] Profile A Active: Hardware Integrated Web Camera")
    elif user_choice == "B":
        video_source = "app/assets/sample_retail.mp4"
        print(f"[CONFIG] Profile B Active: Localized Professional Stock Media ({video_source})")
    elif user_choice == "C":
        video_source = "rtsp://admin:password@192.168.1.100:554/stream1"
        print("[CONFIG] Profile C Active: Commercial CCTV Low-Latency Network Stream")
    else:
        print(f"[ERROR] Signature '{user_choice}' recognized as invalid. Defaulting to Profile B.")
        video_source = "app/assets/sample_retail.mp4"
        user_choice = "B"

    print("=" * 50)

    app.state.video_stream = ThreadedVideoIngest(source=video_source)
    app.state.video_stream.start_processing()

    yield

    print("[SHUTDOWN] Safely unlinking background media streams...")
    stop_method = getattr(app.state.video_stream, "stop_processing", None)
    if stop_method is None:
        stop_method = getattr(app.state.video_stream, "stop", None)
    if stop_method:
        stop_method()
    else:
        print("[SHUTDOWN] No stop method found on video stream object.")

app = FastAPI(lifespan=lifespan)

#  2. INCLUDE YOUR ROUTERS HERE SO SWAGGER CAN SEE THEM
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(store.router, prefix="/api/store", tags=["Store Analytics"])

@app.get("/")
def home():
    return {
        "status": "Attention Mapping System Active",
        "active_profile": os.getenv("VIDEO_SOURCE_CHOICE", "B").upper()
    }