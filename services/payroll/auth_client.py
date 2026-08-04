import httpx
from fastapi import HTTPException, status

from app.config import settings


def get_user_profile(user_id: int) -> dict:
    """Запрашивает профиль пользователя в auth-service (внутренний API)."""
    url = f"{settings.AUTH_SERVICE_URL}/internal/users/{user_id}/profile"
    try:
        resp = httpx.get(
            url,
            headers={"X-Internal-Token": settings.INTERNAL_API_TOKEN},
            timeout=10.0,
        )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис авторизации недоступен",
        )
    if resp.status_code == 404:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ошибка сервиса авторизации",
        )
    return resp.json()
