"""PIX-service — «Калькулятор внедрения PIX Operator».

Сервис без своей БД: отдаёт самодостаточную статическую страницу калькулятора.
Все вычисления выполняются в браузере, состояние на сервере не хранится.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Bit_micro_serverse — pix-service", version="0.1.0")


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "pix-service"}


# Статика монтируется в корень сервиса; префикс /pix срезают шлюзы
# (local_gateway и nginx), поэтому и локально, и в Docker страница
# доступна как /pix/.
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
