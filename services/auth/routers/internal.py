from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Grade, GradeTier, User


router = APIRouter(prefix="/internal", tags=["internal"])


def verify_internal_token(x_internal_token: str = Header(default="")) -> None:
    if not settings.INTERNAL_API_TOKEN or x_internal_token != settings.INTERNAL_API_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


class TierOut(BaseModel):
    min_pct: float
    bonus_percent: float


class GradeOut(BaseModel):
    id: str
    name: str
    base_salary: float
    bonus_percent: float
    service_factor: float
    has_plan: bool
    plan_margin: Optional[float] = None
    kpi2_enabled: bool = False
    kpi2_bonus_percent: float = 5.0
    kpi2_min_retention_pct: float = 80.0
    scheme: str = "margin"
    kpi2_bonus_type: str = "percent"
    kpi2_fixed_amount: float = 0.0
    tiers: List[TierOut] = []


class ProfileOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    department_id: int
    department_code: str
    department_name: str
    position_id: int
    position_name: str
    grade: Optional[GradeOut] = None


class MemberOut(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    is_active: bool
    position_name: str
    grade_id: Optional[str] = None
    grade_name: Optional[str] = None
    base_salary: Optional[float] = None


def _grade_out(grade: Grade, db: Session) -> GradeOut:
    tiers = db.scalars(
        select(GradeTier).where(GradeTier.grade_id == grade.id).order_by(GradeTier.min_pct)
    ).all()
    return GradeOut(
        id=grade.id,
        name=grade.name,
        base_salary=float(grade.base_salary),
        bonus_percent=float(grade.bonus_percent),
        service_factor=float(grade.service_factor),
        has_plan=bool(grade.has_plan),
        plan_margin=(float(grade.plan_margin) if grade.plan_margin is not None else None),
        kpi2_enabled=bool(grade.kpi2_enabled),
        kpi2_bonus_percent=float(grade.kpi2_bonus_percent),
        kpi2_min_retention_pct=float(grade.kpi2_min_retention_pct),
        scheme=grade.scheme or "margin",
        kpi2_bonus_type=grade.kpi2_bonus_type or "percent",
        kpi2_fixed_amount=float(grade.kpi2_fixed_amount or 0),
        tiers=[TierOut(min_pct=float(t.min_pct), bonus_percent=float(t.bonus_percent)) for t in tiers],
    )


@router.get("/users/{user_id}/profile", response_model=ProfileOut,
            dependencies=[Depends(verify_internal_token)])
def user_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    return ProfileOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=bool(user.is_active),
        department_id=user.department_id,
        department_code=user.department.code if user.department else "",
        department_name=user.department.name if user.department else "",
        position_id=user.position_id,
        position_name=user.position.name if user.position else "",
        grade=_grade_out(user.grade, db) if user.grade else None,
    )


@router.get("/departments/{department_id}/members", response_model=List[MemberOut],
            dependencies=[Depends(verify_internal_token)])
def department_members(
    department_id: int,
    role: Optional[str] = Query(default=None),
    active_only: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    stmt = select(User).where(User.department_id == department_id)
    if role:
        stmt = stmt.where(User.role == role)
    if active_only:
        stmt = stmt.where(User.is_active.is_(True))
    stmt = stmt.order_by(User.full_name)
    rows = db.scalars(stmt).all()
    return [
        MemberOut(
            id=u.id,
            full_name=u.full_name,
            email=u.email,
            role=u.role,
            is_active=bool(u.is_active),
            position_name=u.position.name if u.position else "",
            grade_id=u.grade_id,
            grade_name=u.grade.name if u.grade else None,
            base_salary=float(u.grade.base_salary) if u.grade else None,
        )
        for u in rows
    ]
