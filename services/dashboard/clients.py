import httpx
from fastapi import HTTPException, status

from app.config import settings


def _headers() -> dict:
    return {"X-Internal-Token": settings.INTERNAL_API_TOKEN}


def get_department_members(department_id: int, role: str = "manager") -> list[dict]:
    """Сотрудники отдела из auth-service."""
    url = f"{settings.AUTH_SERVICE_URL}/internal/departments/{department_id}/members"
    try:
        resp = httpx.get(url, params={"role": role, "active_only": True}, headers=_headers(), timeout=10.0)
    except httpx.HTTPError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Сервис авторизации недоступен")
    if resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Ошибка сервиса авторизации")
    return resp.json()


def get_user_profile(user_id: int) -> dict:
    url = f"{settings.AUTH_SERVICE_URL}/internal/users/{user_id}/profile"
    try:
        resp = httpx.get(url, headers=_headers(), timeout=10.0)
    except httpx.HTTPError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Сервис авторизации недоступен")
    if resp.status_code == 404:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
    if resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Ошибка сервиса авторизации")
    return resp.json()


def get_latest_records(periods: list[str], user_ids: list[int]) -> dict:
    """Последние расчёты и себестоимость из payroll-service."""
    url = f"{settings.PAYROLL_SERVICE_URL}/internal/records/latest"
    try:
        resp = httpx.post(url, json={"periods": periods, "user_ids": user_ids}, headers=_headers(), timeout=20.0)
    except httpx.HTTPError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Сервис расчёта ЗП недоступен")
    if resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Ошибка сервиса расчёта ЗП")
    return resp.json()
