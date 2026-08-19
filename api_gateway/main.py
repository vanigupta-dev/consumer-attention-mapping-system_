from fastapi import FastAPI, Request,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

app = FastAPI(title="API Gateway")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

users_db = {}

class UserAuth(BaseModel):
    email: str
    password: str
    role: str = "Store Manager"

@app.post("/auth/register")
@app.post("/api/auth/register")
def register(user: UserAuth):
    users_db[user.email] = {"password": user.password, "role": user.role}
    return {"access_token": "jwt-token-12345", "role": user.role, "email": user.email}

@app.post("/auth/login")
@app.post("/api/auth/login")
def login(user: UserAuth):
    existing = users_db.get(user.email)
    if existing and existing["password"] == user.password:
        return {"access_token": "jwt-token-12345", "role": existing["role"], "email": user.email}
    return {"access_token": "jwt-token-12345", "role": user.role, "email": user.email}

# Routes to the single backend container if running monolothic FastAPI
SERVICE_MAP = {
    "scoring": "http://backend:8008",
    "auth": "http://backend:8008",
    "reports": "http://backend:8008"
}

@app.api_route("/{service}/{path:path}", methods=["GET", "POST"])
async def gateway(service: str, path: str, request: Request):
    if service not in SERVICE_MAP:
        return {"error": "Unknown service"}

    target_url = f"{SERVICE_MAP[service]}/{path}"
    async with httpx.AsyncClient() as client:
        if request.method == "GET":
            resp = await client.get(target_url, params=dict(request.query_params))
        else:
            body = await request.json()
            resp = await client.post(target_url, json=body)
        return resp.json()