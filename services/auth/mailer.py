"""Отправка писем через SMTP (стандартная библиотека, без внешних зависимостей).

Если SMTP не настроен (SMTP_HOST пуст) — сервис работает в dev-режиме:
код сброса пароля печатается в консоль, письма не отправляются.
"""
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from app.config import settings

SMTP_TIMEOUT_SECONDS = 15


def smtp_configured() -> bool:
    return bool(settings.SMTP_HOST)


def _send(to_email: str, subject: str, text_body: str, html_body: str) -> None:
    """Синхронная отправка письма. Бросает исключение при ошибке."""
    from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
    if not from_email:
        raise RuntimeError("Не задан SMTP_FROM_EMAIL / SMTP_USER")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((str(Header(settings.SMTP_FROM_NAME, "utf-8")), from_email))
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    if settings.SMTP_USE_SSL:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT,
                              timeout=SMTP_TIMEOUT_SECONDS, context=context) as server:
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(from_email, [to_email], msg.as_string())
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT,
                          timeout=SMTP_TIMEOUT_SECONDS) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(from_email, [to_email], msg.as_string())


def send_password_reset_code(to_email: str, code: str, ttl_minutes: int) -> None:
    subject = f"Код восстановления пароля: {code}"
    text_body = (
        f"Здравствуйте!\n\n"
        f"Вы запросили восстановление пароля в Бит.Serves.\n\n"
        f"Ваш код: {code}\n\n"
        f"Код действует {ttl_minutes} минут. "
        f"Если вы не запрашивали восстановление — просто проигнорируйте это письмо, "
        f"ваш пароль останется прежним.\n\n"
        f"— Команда Бит.Serves"
    )
    html_body = f"""\
<!DOCTYPE html>
<html lang="ru">
<body style="margin:0;padding:24px;background:#f4f6fb;font-family:Segoe UI,Arial,sans-serif">
  <div style="max-width:480px;margin:0 auto;background:#ffffff;border-radius:16px;
              padding:32px;box-shadow:0 4px 16px rgba(0,0,0,.08)">
    <div style="font-size:18px;font-weight:800;color:#1a1f36;margin-bottom:6px">Бит.Serves</div>
    <div style="font-size:14px;color:#5a6478;margin-bottom:24px">Восстановление пароля</div>
    <div style="font-size:14px;color:#1a1f36;line-height:1.6">
      Вы запросили восстановление пароля. Введите этот код в форме на сайте:
    </div>
    <div style="margin:24px 0;text-align:center">
      <span style="display:inline-block;font-size:32px;font-weight:800;letter-spacing:8px;
                   color:#0a54c9;background:#eef4ff;border-radius:12px;padding:14px 28px">{code}</span>
    </div>
    <div style="font-size:13px;color:#5a6478;line-height:1.6">
      Код действует <b>{ttl_minutes} минут</b>.<br>
      Если вы не запрашивали восстановление — просто проигнорируйте письмо,
      ваш пароль останется прежним.
    </div>
  </div>
</body>
</html>"""
    _send(to_email, subject, text_body, html_body)
