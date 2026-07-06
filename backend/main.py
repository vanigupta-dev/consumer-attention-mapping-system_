from fastapi import FastAPI
from app.database.connection import engine, Base
from app.routers import auth, store

# Command SQLAlchemy to auto-build database tables upon activation
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Consumer Attention Mapping System Engine", version="1.0.0")

# FIX: Add .router after the file names so FastAPI finds the variables inside them
app.include_router(auth.router)
app.include_router(store.router)

@app.get("/")
def structural_ping():
    return {"gateway_status": "Operational", "framework": "FastAPI Layer Secured"}