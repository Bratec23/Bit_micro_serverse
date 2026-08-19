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

# Статические сервисы-витрины: (url-префикс, порт). Префикс срезается —
# сервисы отдают свои страницы из корня.
#   funnel-service (:8007) — воронка продаж «Промышленная маркировка»
#   pix-service    (:8006) — калькулятор внедрения PIX Operator
STATIC_SERVICES = [
    ("/funnel", 8007),
    ("/pix", 8006),
]

HOP_HEADERS = {"connection", "keep-alive", "transfer-encoding", "content-encoding", "content-length"}

app = FastAPI(title="Bit.Serves — local gateway")
client = httpx.Client(timeout=30.0)


def _target(path: str) -> int | None:
    for prefix, port in ROUTES:
        if path.startswith(prefix):
            return port
    return None


def _register_static_service(prefix: str, port: int) -> None:
    async def proxy_static(request: Request):
        # срезаем префикс — сервис отдаёт статику из корня
        path = request.url.path[len(prefix):] or "/"
        url = f"http://127.0.0.1:{port}{path}"
        if request.url.query:
            url += "?" + request.url.query
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
        resp = client.request("GET", url, headers=headers)
        out_headers = {k: v for k, v in resp.headers.items() if k.lower() not in HOP_HEADERS}
        return Response(content=resp.content, status_code=resp.status_code, headers=out_headers)

    app.add_api_route(prefix, proxy_static, methods=["GET"])
    app.add_api_route(prefix + "/{path:path}", proxy_static, methods=["GET"])


for _prefix, _port in STATIC_SERVICES:
    _register_static_service(_prefix, _port)


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
