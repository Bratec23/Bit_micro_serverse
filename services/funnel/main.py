"""Funnel-service — «Воронка продаж · Промышленная маркировка».

Сервис без своей БД: отдаёт самодостаточную статическую страницу дашборда.
Все данные воронки хранятся в браузере пользователя (localStorage),
резервное копирование — через экспорт/импорт в самом дашборде.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Bit_micro_serverse — funnel-service", version="0.1.0")


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "funnel-service"}


# Статика монтируется в корень сервиса; префикс /funnel срезают шлюзы
# (local_gateway и nginx), поэтому и локально, и в Docker страница
# доступна как /funnel/.
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
