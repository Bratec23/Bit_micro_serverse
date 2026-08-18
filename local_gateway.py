"""Локальный gateway для разработки без Docker: проксирует /api/* на сервисы и раздаёт frontend."""
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

# (префикс, порт сервиса)
ROUTES = [
    ("/api/auth/", 8001),
    ("/api/admin/", 8001),
    ("/api/departments", 8001),
    ("/api/positions", 8001),
    ("/api/grades", 8001),
    ("/api/payroll/", 8002),
    ("/api/head/", 8003),
    ("/api/kp/", 8004),
    ("/health", 8001),
]

# funnel-service (:8005) — статический дашборд воронки продаж.
# Префикс /funnel срезается: сервис отдаёт страницу из своего корня.
FUNNEL_PORT = 8005

HOP_HEADERS = {"connection", "keep-alive", "transfer-encoding", "content-encoding", "content-length"}

app = FastAPI(title="Bit.Serves — local gateway")
client = httpx.Client(timeout=30.0)


def _target(path: str) -> int | None:
    for prefix, port in ROUTES:
        if path.startswith(prefix):
            return port
    return None


@app.api_route("/funnel", methods=["GET"])
@app.api_route("/funnel/{path:path}", methods=["GET"])
async def proxy_funnel(request: Request):
    # срезаем префикс /funnel — сервис отдаёт статику из корня
    path = request.url.path[len("/funnel"):] or "/"
    url = f"http://127.0.0.1:{FUNNEL_PORT}{path}"
    if request.url.query:
        url += "?" + request.url.query
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
    resp = client.request("GET", url, headers=headers)
    out_headers = {k: v for k, v in resp.headers.items() if k.lower() not in HOP_HEADERS}
    return Response(content=resp.content, status_code=resp.status_code, headers=out_headers)


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
@app.api_route("/health", methods=["GET"])
async def proxy(request: Request):
    port = _target(request.url.path)
    if port is None:
        return Response(status_code=404, content='{"detail":"Not Found"}', media_type="application/json")
    url = f"http://127.0.0.1:{port}{request.url.path}"
    if request.url.query:
        url += "?" + request.url.query
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
    body = await request.body()
    resp = client.request(request.method, url, headers=headers, content=body or None)
    out_headers = {k: v for k, v in resp.headers.items() if k.lower() not in HOP_HEADERS}
    return Response(content=resp.content, status_code=resp.status_code, headers=out_headers)


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")
