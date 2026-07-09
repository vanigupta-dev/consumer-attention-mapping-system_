from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.db import engine, Base
from app.api import auth, store
from app.services.video import ThreadedVideoIngest

# 1. Define the modern lifespan manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs exactly when the server boots up
    print("[STARTUP] Triggering automatic database migrations...")
    Base.metadata.create_all(bind=engine)

    print("[STARTUP] Spawning OpenCV background processing thread...")
    stream_tester = ThreadedVideoIngest(source="0")  # Uses default webcam index
    stream_tester.start_processing()

    yield  # The application runs here while waiting

    # This runs right when you shut down the server (CTRL+C)
    print("[SHUTDOWN] Cleaning up background video streams...")
    stream_tester.stop_processing()

# 2. Pass the lifespan manager directly into your FastAPI app instance
app = FastAPI(
    title="Consumer Attention Mapping System Engine Base",
    lifespan=lifespan
)

# 3. Mount contracts cleanly onto prefixed operational router gateways
app.include_router(auth.router, prefix="/api/auth", tags=["Core Authentication"])
app.include_router(store.router, prefix="/api", tags=["Operational Store Layouts"])

@app.get("/")
def structural_root_check():
    return {
        "status": "Enterprise Core System Ready",
        "scope": "Milestone 1 Core Integrity Maintained"
    }