from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth_client import get_user_profile
from app.config import settings
from app.database import get_db
from app.export import generate_payroll_xlsx
from app.models import CostPriceRecord, PayrollRecord
from app.security import decode_access_token


router = APIRouter(prefix="/api/payroll", tags=["payroll"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

PAYROLL_DEPARTMENT_CODES = {"dev_art", "abt"}

# ===== Мотивация отдела АБТ (СБИС) =====
# базовые ставки по колонкам выполнения нормы реализации ДС:
#   колонка 0: 0–89,99% · колонка 1: 90–99,99% · колонка 2: 100–109,99%
ABT_BASE_RATES = {
    "new": [8.0, 10.0, 13.0],        # новые продажи
    "expansion": [7.0, 9.0, 11.0],   # расширение
    "upgrade": [5.0, 7.0, 9.0],      # апгрейд
    "renew": [1.2, 1.3, 1.5],        # продление без изменений
}
# перевыполнение (>=110%): меняется только ставка «новых продаж», типы 2–4 — без изменений (колонка 2)
ABT_OVER_RATES = [(130.0, 20.0), (120.0, 17.0), (110.0, 15.0)]  # (порог выполнения %, ставка %)
ABT_SBIS_GOODS_RATE = 10.0  # «Товары СБИС» — всегда 10%


def get_current_profile(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_access_token(token)
    user_id = payload.get("sub") if payload else None
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен")
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен")
    profile = get_user_profile(uid)
    if not profile.get("is_active"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Учётная запись деактивирована")
    return profile


class PayrollCalcIn(BaseModel):
    period: str = Field(description="ГГГГ-ММ, например 2026-07")
    worked_days: int = Field(ge=0, le=31)
    working_days: int = Field(ge=1, le=31)
    service_margin: float = Field(ge=0, default=0)
    goods_margin: float = Field(ge=0, default=0)
    month_margin: float = Field(ge=0, default=0, description="Маржа за месяц — для выполнения плана и ступеней (АРТ)")
    tax_rate: float = Field(ge=0, le=100, default=13.0)
    kpi2_revenue: float = Field(ge=0, default=0)
    kpi2_retention_pct: float = Field(ge=0, le=100, default=0)
    # АБТ: реализация по типам продаж
    sales_new: float = Field(ge=0, default=0)
    sales_expansion: float = Field(ge=0, default=0)
    sales_upgrade: float = Field(ge=0, default=0)
    sales_renew: float = Field(ge=0, default=0)
    sbis_goods: float = Field(ge=0, default=0)


class PayrollOut(BaseModel):
    id: int
    period: str
    worked_days: int
    working_days: int
    service_margin: float
    goods_margin: float
    month_margin: float = 0
    bonus_percent: float
    service_factor: float
    base_salary: float
    accrued_base: float
    services_bonus: float
    goods_bonus: float
    bonus_total: float
    tax_rate: float
    gross_pay: float
    tax_amount: float
    net_pay: float
    grade_id: str
    grade_name: str
    has_plan: bool = False
    plan_margin: Optional[float] = None
    margin_total: float = 0
    margin_for_plan: float = 0
    performance_pct: Optional[float] = None
    bonus_total_with_kpi2: float = 0
    kpi2_enabled: bool = False
    kpi2_revenue: float = 0
    kpi2_retention_pct: float = 0
    kpi2_bonus_amount: float = 0
    kpi2_paid: bool = False
    kpi2_bonus_percent: float = 5.0
    kpi2_min_retention_pct: float = 80.0
    scheme: str = "margin"
    sales_new: float = 0
    sales_expansion: float = 0
    sales_upgrade: float = 0
    sales_renew: float = 0
    sbis_goods: float = 0
    sales_total: float = 0
    bonus_new: float = 0
    bonus_expansion: float = 0
    bonus_upgrade: float = 0
    bonus_renew: float = 0
    bonus_sbis_goods: float = 0

    class Config:
        from_attributes = False


def _ensure_can_calculate(profile: dict) -> None:
    if profile.get("department_code") not in PAYROLL_DEPARTMENT_CODES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Расчёт заработной платы недоступен для вашего отдела",
        )


def _margin_for_plan(service_margin: float, goods_margin: float) -> float:
    return round((float(service_margin) + float(goods_margin)) * (1 - settings.VAT_RATE_PERCENT / 100), 2)


def _resolve_bonus_percent(grade: dict, margin_for_plan: float) -> float:
    if not grade.get("has_plan") or grade.get("plan_margin") is None or float(grade["plan_margin"]) <= 0:
        return float(grade.get("bonus_percent", 0))
    if margin_for_plan <= 0:
        return 0.0
    plan = float(grade["plan_margin"])
    performance_pct = margin_for_plan / plan * 100
    tiers = sorted(grade.get("tiers", []), key=lambda t: float(t["min_pct"]), reverse=True)
    for tier in tiers:
        if performance_pct >= float(tier["min_pct"]):
            return float(tier["bonus_percent"])
    return 0.0


def _calc_kpi2(grade: dict, kpi2_revenue: float, kpi2_retention_pct: float) -> tuple[float, bool]:
    if not grade.get("kpi2_enabled"):
        return 0.0, False
    if float(kpi2_retention_pct) < float(grade.get("kpi2_min_retention_pct", 80.0)):
        return 0.0, False
    if grade.get("kpi2_bonus_type") == "fixed":
        # фиксированная премия (АБТ): достаточно сохранности, приход не нужен
        return round(float(grade.get("kpi2_fixed_amount", 0)), 2), True
    if kpi2_revenue <= 0:
        return 0.0, False
    bonus = round(float(kpi2_revenue) * float(grade.get("kpi2_bonus_percent", 5.0)) / 100, 2)
    return bonus, True


def _abt_rates(grade: dict, total_ds: float) -> tuple[dict, float | None]:
    """Ставки по типам продаж и % выполнения нормы реализации ДС."""
    plan = float(grade["plan_margin"]) if grade.get("plan_margin") is not None else 0.0
    has_plan = bool(grade.get("has_plan")) and plan > 0
    performance_pct = round(total_ds / plan * 100, 2) if has_plan else None
    if performance_pct is None:
        col = 0  # без плана — базовая колонка
    elif performance_pct < 90:
        col = 0
    elif performance_pct < 100:
        col = 1
    else:
        col = 2
    rates = {k: v[col] for k, v in ABT_BASE_RATES.items()}
    if performance_pct is not None and performance_pct >= 110:
        # перевыполнение: только «новые продажи» по шкале оплат, типы 2–4 — колонка 2 без изменений
        for threshold, rate in ABT_OVER_RATES:
            if performance_pct >= threshold:
                rates["new"] = rate
                break
    return rates, performance_pct


def _calc_abt(grade: dict, p: PayrollCalcIn, kpi2_bonus: float) -> dict:
    """Расчёт по схеме АБТ: оклад + проценты от реализации по типам продаж + KPI2."""
    total_ds = round(p.sales_new + p.sales_expansion + p.sales_upgrade + p.sales_renew, 2)
    rates, performance_pct = _abt_rates(grade, total_ds)
    bonus_new = round(p.sales_new * rates["new"] / 100, 2)
    bonus_expansion = round(p.sales_expansion * rates["expansion"] / 100, 2)
    bonus_upgrade = round(p.sales_upgrade * rates["upgrade"] / 100, 2)
    bonus_renew = round(p.sales_renew * rates["renew"] / 100, 2)
    bonus_sbis_goods = round(p.sbis_goods * ABT_SBIS_GOODS_RATE / 100, 2)
    services_bonus = round(bonus_new + bonus_expansion + bonus_upgrade + bonus_renew, 2)
    bonus_total = round(services_bonus + bonus_sbis_goods, 2)
    accrued_base = round(float(grade["base_salary"]) * p.worked_days / p.working_days, 2)
    gross_pay = round(accrued_base + bonus_total + kpi2_bonus, 2)
    tax_amount = round(gross_pay * p.tax_rate / 100, 2)
    net_pay = round(gross_pay - tax_amount, 2)
    return {
        "accrued_base": accrued_base,
        "services_bonus": services_bonus,
        "goods_bonus": bonus_sbis_goods,
        "bonus_total": bonus_total,
        "gross_pay": gross_pay,
        "tax_amount": tax_amount,
        "net_pay": net_pay,
        "bonus_new": bonus_new,
        "bonus_expansion": bonus_expansion,
        "bonus_upgrade": bonus_upgrade,
        "bonus_renew": bonus_renew,
        "bonus_sbis_goods": bonus_sbis_goods,
        "margin_for_plan": total_ds,
        "performance_pct": performance_pct,
        "rate_new": rates["new"],
        "rate_expansion": rates["expansion"],
        "rate_upgrade": rates["upgrade"],
        "rate_renew": rates["renew"],
    }


def _calc(base_salary: float, bonus_percent: float, service_factor: float, p: PayrollCalcIn, kpi2_bonus: float = 0) -> dict:
    accrued_base = round(base_salary * p.worked_days / p.working_days, 2)
    services_bonus = round(p.service_margin * service_factor * bonus_percent / 100, 2)
    goods_bonus = round(p.goods_margin * bonus_percent / 100, 2)
    bonus_total = round(services_bonus + goods_bonus, 2)
    gross_pay = round(accrued_base + bonus_total + kpi2_bonus, 2)
    tax_amount = round(gross_pay * p.tax_rate / 100, 2)
    net_pay = round(gross_pay - tax_amount, 2)
    return {
        "accrued_base": accrued_base,
        "services_bonus": services_bonus,
        "goods_bonus": goods_bonus,
        "bonus_total": bonus_total,
        "gross_pay": gross_pay,
        "tax_amount": tax_amount,
        "net_pay": net_pay,
    }


def _payroll_out(rec: PayrollRecord) -> dict:
    plan_margin = float(rec.plan_margin) if rec.plan_margin is not None else None
    performance_pct = float(rec.performance_pct) if rec.performance_pct is not None else None
    return {
        "id": rec.id,
        "period": rec.period,
        "worked_days": rec.worked_days,
        "working_days": rec.working_days,
        "service_margin": float(rec.service_margin),
        "goods_margin": float(rec.goods_margin),
        "month_margin": float(rec.month_margin),
        "bonus_percent": float(rec.bonus_percent),
        "service_factor": float(rec.service_factor),
        "base_salary": float(rec.base_salary),
        "accrued_base": float(rec.accrued_base),
        "services_bonus": float(rec.services_bonus),
        "goods_bonus": float(rec.goods_bonus),
        "bonus_total": float(rec.bonus_total),
        "bonus_total_with_kpi2": round(float(rec.bonus_total) + float(rec.kpi2_bonus_amount), 2),
        "tax_rate": float(rec.tax_rate),
        "gross_pay": float(rec.gross_pay),
        "tax_amount": float(rec.tax_amount),
        "net_pay": float(rec.net_pay),
        "grade_id": rec.grade_id,
        "grade_name": rec.grade_name or rec.grade_id,
        "has_plan": bool(rec.has_plan),
        "plan_margin": plan_margin,
        "margin_total": round(float(rec.service_margin) + float(rec.goods_margin), 2),
        "margin_for_plan": float(rec.margin_for_plan),
        "performance_pct": performance_pct,
        "kpi2_enabled": bool(rec.kpi2_enabled),
        "kpi2_revenue": float(rec.kpi2_revenue),
        "kpi2_retention_pct": float(rec.kpi2_retention_pct),
        "kpi2_bonus_amount": float(rec.kpi2_bonus_amount),
        "kpi2_paid": bool(rec.kpi2_paid),
        "kpi2_bonus_percent": float(rec.grade_kpi2_bonus_percent),
        "kpi2_min_retention_pct": float(rec.grade_kpi2_min_retention_pct),
        "scheme": rec.scheme or "margin",
        "sales_new": float(rec.sales_new),
        "sales_expansion": float(rec.sales_expansion),
        "sales_upgrade": float(rec.sales_upgrade),
        "sales_renew": float(rec.sales_renew),
        "sbis_goods": float(rec.sbis_goods),
        "sales_total": round(
            float(rec.sales_new) + float(rec.sales_expansion) + float(rec.sales_upgrade)
            + float(rec.sales_renew) + float(rec.sbis_goods), 2),
        "bonus_new": float(rec.bonus_new),
        "bonus_expansion": float(rec.bonus_expansion),
        "bonus_upgrade": float(rec.bonus_upgrade),
        "bonus_renew": float(rec.bonus_renew),
        "bonus_sbis_goods": float(rec.bonus_sbis_goods),
    }


@router.post("/calculate", response_model=PayrollOut, status_code=status.HTTP_201_CREATED)
def calculate_payroll(payload: PayrollCalcIn, db: Session = Depends(get_db), profile: dict = Depends(get_current_profile)):
    _ensure_can_calculate(profile)
    if payload.worked_days > payload.working_days:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Отработано дней не может быть больше рабочих дней в месяце")
    grade = profile.get("grade")
    if not grade:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователю не назначен грейд")
    base_salary = float(grade["base_salary"])
    service_factor = float(grade["service_factor"])
    scheme = grade.get("scheme") or "margin"
    kpi2_bonus, kpi2_paid = _calc_kpi2(grade, payload.kpi2_revenue, payload.kpi2_retention_pct)
    has_plan = bool(grade.get("has_plan"))
    plan_margin = float(grade["plan_margin"]) if grade.get("plan_margin") is not None else None

    if scheme == "abt":
        calc = _calc_abt(grade, payload, kpi2_bonus)
        margin_for_plan = calc.pop("margin_for_plan")
        performance_pct = calc.pop("performance_pct")
        calc.pop("rate_new"); calc.pop("rate_expansion"); calc.pop("rate_upgrade"); calc.pop("rate_renew")
        bonus_percent = 0.0
        record = PayrollRecord(
            user_id=profile["id"],
            period=payload.period,
            worked_days=payload.worked_days,
            working_days=payload.working_days,
            service_margin=0,
            goods_margin=0,
            bonus_percent=bonus_percent,
            service_factor=service_factor,
            base_salary=base_salary,
            tax_rate=payload.tax_rate,
            grade_id=grade["id"],
            grade_name=grade.get("name", grade["id"]),
            has_plan=has_plan,
            plan_margin=plan_margin,
            margin_for_plan=margin_for_plan,
            performance_pct=performance_pct,
            kpi2_enabled=bool(grade.get("kpi2_enabled")),
            kpi2_revenue=payload.kpi2_revenue,
            kpi2_retention_pct=payload.kpi2_retention_pct,
            kpi2_bonus_amount=kpi2_bonus,
            kpi2_paid=kpi2_paid,
            grade_kpi2_bonus_percent=float(grade.get("kpi2_bonus_percent", 5.0)),
            grade_kpi2_min_retention_pct=float(grade.get("kpi2_min_retention_pct", 80.0)),
            scheme="abt",
            sales_new=payload.sales_new,
            sales_expansion=payload.sales_expansion,
            sales_upgrade=payload.sales_upgrade,
            sales_renew=payload.sales_renew,
            sbis_goods=payload.sbis_goods,
            **calc,
        )
    else:
        # АРТ: план и ступени считаются по отдельному показателю «Маржа за месяц»,
        # а премии — по марже услуг/товаров (в них могут быть долги прошлых месяцев)
        margin_for_plan = round(float(payload.month_margin), 2)
        bonus_percent = _resolve_bonus_percent(grade, margin_for_plan)
        calc = _calc(base_salary, bonus_percent, service_factor, payload, kpi2_bonus)
        if has_plan and plan_margin and plan_margin > 0:
            performance_pct = round(margin_for_plan / plan_margin * 100, 2)
        else:
            performance_pct = None
        record = PayrollRecord(
            user_id=profile["id"],
            period=payload.period,
            worked_days=payload.worked_days,
            working_days=payload.working_days,
            service_margin=payload.service_margin,
            goods_margin=payload.goods_margin,
            month_margin=payload.month_margin,
            bonus_percent=bonus_percent,
            service_factor=service_factor,
            base_salary=base_salary,
            tax_rate=payload.tax_rate,
            grade_id=grade["id"],
            grade_name=grade.get("name", grade["id"]),
            has_plan=has_plan,
            plan_margin=plan_margin,
            margin_for_plan=margin_for_plan,
            performance_pct=performance_pct,
            kpi2_enabled=bool(grade.get("kpi2_enabled")),
            kpi2_revenue=payload.kpi2_revenue,
            kpi2_retention_pct=payload.kpi2_retention_pct,
            kpi2_bonus_amount=kpi2_bonus,
            kpi2_paid=kpi2_paid,
            grade_kpi2_bonus_percent=float(grade.get("kpi2_bonus_percent", 5.0)),
            grade_kpi2_min_retention_pct=float(grade.get("kpi2_min_retention_pct", 80.0)),
            scheme="margin",
            **calc,
        )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _payroll_out(record)


@router.get("/history", response_model=List[PayrollOut])
def history(db: Session = Depends(get_db), profile: dict = Depends(get_current_profile)):
    rows = db.scalars(
        select(PayrollRecord)
        .where(PayrollRecord.user_id == profile["id"])
        .order_by(PayrollRecord.created_at.desc())
    ).all()
    return [_payroll_out(r) for r in rows]


class SummaryOut(BaseModel):
    period: str
    record_id: int
    created_at: str
    accrued_base: float
    services_bonus: float
    goods_bonus: float
    bonus_total: float
    bonus_total_with_kpi2: float
    kpi2_bonus_amount: float
    gross_pay: float
    tax_amount: float
    net_pay: float


@router.get("/summary", response_model=List[SummaryOut])
def summary(db: Session = Depends(get_db), profile: dict = Depends(get_current_profile)):
    rows = db.scalars(
        select(PayrollRecord)
        .where(PayrollRecord.user_id == profile["id"])
        .order_by(PayrollRecord.created_at.desc())
    ).all()
    latest_by_period: dict[str, PayrollRecord] = {}
    for r in rows:
        if r.period not in latest_by_period:
            latest_by_period[r.period] = r
    items = list(latest_by_period.values())
    items.sort(key=lambda x: x.period)
    return [
        SummaryOut(
            period=r.period,
            record_id=r.id,
            created_at=r.created_at.strftime("%d.%m.%Y %H:%M") if r.created_at else "",
            accrued_base=float(r.accrued_base),
            services_bonus=float(r.services_bonus),
            goods_bonus=float(r.goods_bonus),
            bonus_total=float(r.bonus_total),
            bonus_total_with_kpi2=round(float(r.bonus_total) + float(r.kpi2_bonus_amount), 2),
            kpi2_bonus_amount=float(r.kpi2_bonus_amount),
            gross_pay=float(r.gross_pay),
            tax_amount=float(r.tax_amount),
            net_pay=float(r.net_pay),
        )
        for r in items
    ]


@router.get("/records/{record_id}/export")
def export_record(record_id: int, db: Session = Depends(get_db), profile: dict = Depends(get_current_profile)):
    record = db.get(PayrollRecord, record_id)
    if not record or record.user_id != profile["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Расчёт не найден")
    content = generate_payroll_xlsx(record, profile)
    safe_name = (profile.get("full_name") or "employee").replace(" ", "_").replace("/", "_")
    ascii_name = f"Raschet_ZP_{record.id}_{record.period}"
    utf8_name = f"Raschet_ZP_{safe_name}_{record.period}.xlsx"
    disposition = f"attachment; filename=\"{ascii_name}.xlsx\"; filename*=UTF-8''{quote(utf8_name)}"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": disposition},
    )


class CostPriceIn(BaseModel):
    period: str = Field(description="ГГГГ-ММ, например 2026-07")
    cost_price: float = Field(ge=0, default=0)


class CostPriceOut(BaseModel):
    period: str
    cost_price: float
    updated_at: str


@router.post("/cost-price", response_model=CostPriceOut)
def save_cost_price(payload: CostPriceIn, db: Session = Depends(get_db), profile: dict = Depends(get_current_profile)):
    existing = db.scalar(
        select(CostPriceRecord).where(
            CostPriceRecord.user_id == profile["id"],
            CostPriceRecord.period == payload.period,
        )
    )
    if existing:
        existing.cost_price = payload.cost_price
    else:
        existing = CostPriceRecord(
            user_id=profile["id"],
            period=payload.period,
            cost_price=payload.cost_price,
        )
        db.add(existing)
    db.commit()
    db.refresh(existing)
    return CostPriceOut(
        period=existing.period,
        cost_price=float(existing.cost_price),
        updated_at=existing.created_at.strftime("%d.%m.%Y %H:%M") if existing.created_at else "",
    )


@router.get("/cost-price", response_model=List[CostPriceOut])
def list_cost_price(
    period: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    profile: dict = Depends(get_current_profile),
):
    stmt = select(CostPriceRecord).where(CostPriceRecord.user_id == profile["id"])
    if period:
        stmt = stmt.where(CostPriceRecord.period == period)
    stmt = stmt.order_by(CostPriceRecord.period.desc())
    rows = db.scalars(stmt).all()
    return [
        CostPriceOut(
            period=r.period,
            cost_price=float(r.cost_price),
            updated_at=r.created_at.strftime("%d.%m.%Y %H:%M") if r.created_at else "",
        )
        for r in rows
    ]
