from fastapi import FastAPI, Request
import httpx

app = FastAPI(title="API Gateway")

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