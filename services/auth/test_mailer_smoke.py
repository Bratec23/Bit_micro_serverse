"""Smoke-тест mailer: письмо собирается и «отправляется» через заглушку SMTP."""
import os
import sys
import types
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./smoke_auth.db")
os.environ["SMTP_HOST"] = "smtp.example.com"
os.environ["SMTP_USER"] = "robot@example.com"
os.environ["SMTP_PASSWORD"] = "secret"
os.environ["SMTP_FROM_EMAIL"] = "robot@example.com"

_pkg_dir = Path(__file__).resolve().parent
_pkg = types.ModuleType("app")
_pkg.__path__ = [str(_pkg_dir)]
sys.modules.setdefault("app", _pkg)

import app.mailer as mailer

assert mailer.smtp_configured() is True

sent = {}


class FakeSMTP_SSL:
    def __init__(self, host, port, timeout=None, context=None):
        sent["host"], sent["port"] = host, port

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def login(self, user, password):
        sent["login"] = (user, password)

    def sendmail(self, from_addr, to_addrs, msg):
        sent["from"], sent["to"], sent["msg"] = from_addr, to_addrs, msg


mailer.smtplib.SMTP_SSL = FakeSMTP_SSL

mailer.send_password_reset_code("manager@example.com", "482913", 15)

assert sent["host"] == "smtp.example.com" and sent["port"] == 465
assert sent["login"] == ("robot@example.com", "secret")
assert sent["to"] == ["manager@example.com"]
assert sent["from"] == "robot@example.com"
import email as _email

parsed = _email.message_from_string(sent["msg"])
bodies = []
for part in parsed.walk():
    if part.get_content_type() in ("text/plain", "text/html"):
        bodies.append(part.get_payload(decode=True).decode("utf-8"))
msg = "\n".join(bodies)
assert "482913" in msg, "код не найден в теле письма"
assert "15" in msg  # TTL в теле письма
assert parsed["To"] == "manager@example.com"
assert parsed["Subject"]  # тема есть (в MIME-кодировке)

print(f"OK: письмо собрано, to={sent['to']}, код и TTL в теле")
print("ВСЕ ТЕСТЫ MAILER ПРОШЛИ")
