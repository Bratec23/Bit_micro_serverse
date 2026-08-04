import sys
import types
from pathlib import Path

# Код сервиса лежит плоско в этой директории; регистрируем её как пакет "app",
# чтобы импорты вида "from app.config import ..." работали и локально, и в Docker.
_pkg_dir = Path(__file__).resolve().parent
_pkg = types.ModuleType("app")
_pkg.__path__ = [str(_pkg_dir)]
sys.modules.setdefault("app", _pkg)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8004,
        reload=False,
        log_level="info",
        access_log=True,
    )
