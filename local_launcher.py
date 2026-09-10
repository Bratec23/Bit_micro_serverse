"""Локальный запуск платформы Бит.Serves без Docker (SQLite вместо PostgreSQL).

Запуск:  python local_launcher.py [--host 0.0.0.0] [--port 8000]
Остановка: Ctrl+C (дочерние сервисы гаснут автоматически).
"""
import argparse
import atexit
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "dev_data"
DATA_DIR.mkdir(exist_ok=True)

BASE_ENV = {
    "SECRET_KEY": "dev-secret-key-change-me",
    "INTERNAL_API_TOKEN": "dev-internal-token",
    "HEAD_REGISTER_PASSWORD": "123456789",
    "AUTH_SERVICE_URL": "http://127.0.0.1:8001",
    "PAYROLL_SERVICE_URL": "http://127.0.0.1:8002",
}

SERVICES = [
    ("auth", 8001, {"DATABASE_URL_OVERRIDE": f"sqlite:///{DATA_DIR / 'auth.db'}"}),
    ("payroll", 8002, {"DATABASE_URL": f"sqlite:///{DATA_DIR / 'payroll.db'}"}),
    ("dashboard", 8003, {}),
    ("kp", 8004, {"DATABASE_URL": f"sqlite:///{DATA_DIR / 'kp.db'}"}),
    ("funnel", 8007, {}),
    ("pix", 8006, {}),
]

procs: list[subprocess.Popen] = []


def _stop_all():
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass
    for p in procs:
        try:
            p.wait(timeout=5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass


def kill_stale_project_processes() -> None:
    """Гасим «сирот» прошлых запусков: все python-процессы, чей путь/команда
    содержит имя папки проекта (кроме текущего процесса).

    Без этого каждый повторный запуск start.bat плодил копии run_server.py:
    stop.bat убивал только процессы, слушающие порты, а осиротевшие дочерние
    процессы оставались жить и ели RAM/CPU.
    """
    if os.name != "nt":
        return
    me = os.getpid()
    marker = ROOT.name  # например, "Bit_micro_serverse"
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
        f"Where-Object {{ $_.ProcessId -ne {me} -and ("
        f"$_.ExecutablePath -like '*{marker}*' -or $_.CommandLine -like '*{marker}*') }} | "
        "ForEach-Object { Write-Output ('kill ' + $_.ProcessId + ' ' + $_.Name); "
        "Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    try:
        out = subprocess.run(
            [_powershell(), "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=30,
        )
        for line in (out.stdout or "").splitlines():
            print(f"[launcher] stale: {line}", flush=True)
    except Exception as e:
        print(f"[launcher] WARNING: не удалось зачистить старые процессы: {e}", flush=True)


def _powershell() -> str:
    import shutil
    return (
        shutil.which("powershell")
        or shutil.which("powershell.exe")
        or r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    )


atexit.register(_stop_all)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", "-H", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", "-p", type=int,
                        default=int(os.environ.get("PORT", "8000")))
    args, _unknown = parser.parse_known_args()

    # Зачистка «сирот» прошлых запусков — иначе каждый старт плодит копии сервисов
    kill_stale_project_processes()
    time.sleep(1)  # даём освободиться портам

    import socket
    for name, port, _ in SERVICES:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                print(f"[launcher] WARNING: порт {port} уже занят — {name}-service может подняться на старом процессе!", flush=True)

    for name, port, extra in SERVICES:
        env = dict(os.environ)
        env.update(BASE_ENV)
        env.update(extra)
        p = subprocess.Popen(
            [sys.executable, "run_server.py"],
            cwd=ROOT / "services" / name,
            env=env,
        )
        procs.append(p)
        print(f"[launcher] {name}-service -> :{port} (pid {p.pid})", flush=True)

    import urllib.request
    for name, port, _ in SERVICES:
        url = f"http://127.0.0.1:{port}/health"
        for _ in range(60):
            try:
                with urllib.request.urlopen(url, timeout=2) as r:
                    if r.status == 200:
                        print(f"[launcher] {name} health OK", flush=True)
                        break
            except Exception:
                time.sleep(0.5)
        else:
            print(f"[launcher] WARNING: {name} не поднялся на :{port}", flush=True)

    print(f"[launcher] gateway -> http://127.0.0.1:{args.port}", flush=True)
    print("[launcher] Ctrl+C для остановки", flush=True)

    import uvicorn
    uvicorn.run("local_gateway:app", host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
