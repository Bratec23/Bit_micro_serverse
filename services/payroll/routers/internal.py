from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import CostPriceRecord, PayrollRecord


router = APIRouter(prefix="/internal", tags=["internal"])


def verify_internal_token(x_internal_token: str = Header(default="")) -> None:
    if not settings.INTERNAL_API_TOKEN or x_internal_token != settings.INTERNAL_API_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


class LatestRequest(BaseModel):
    periods: List[str] = Field(min_length=1, max_length=120)
    user_ids: List[int] = Field(min_length=1, max_length=500)


class RecordBrief(BaseModel):
    id: int
    period: str
    service_margin: float
    goods_margin: float
    scheme: str = "margin"
    sales_total: float = 0
    bonus_total: float
    bonus_total_with_kpi2: float
    gross_pay: float
    tax_amount: float
    net_pay: float
    base_salary: float
    kpi2_revenue: float
    kpi2_retention_pct: float
    kpi2_bonus_amount: float
    kpi2_paid: bool
    created_at: str


class LatestResponse(BaseModel):
    # records[user_id][period] -> RecordBrief | None
    records: Dict[int, Dict[str, Optional[RecordBrief]]]
    # cost_prices[user_id][period] -> float
    cost_prices: Dict[int, Dict[str, float]]


def _record_brief(rec: PayrollRecord) -> RecordBrief:
    return RecordBrief(
        id=rec.id,
        period=rec.period,
        service_margin=float(rec.service_margin),
        goods_margin=float(rec.goods_margin),
        scheme=rec.scheme or "margin",
        sales_total=round(
            float(rec.sales_new) + float(rec.sales_expansion) + float(rec.sales_upgrade)
            + float(rec.sales_renew) + float(rec.sbis_goods), 2),
        bonus_total=float(rec.bonus_total),
        bonus_total_with_kpi2=round(float(rec.bonus_total) + float(rec.kpi2_bonus_amount) + float(rec.kpi3_bonus_amount), 2),
        gross_pay=float(rec.gross_pay),
        tax_amount=float(rec.tax_amount),
        net_pay=float(rec.net_pay),
        base_salary=float(rec.base_salary),
        kpi2_revenue=float(rec.kpi2_revenue),
        kpi2_retention_pct=float(rec.kpi2_retention_pct),
        kpi2_bonus_amount=float(rec.kpi2_bonus_amount),
        kpi2_paid=bool(rec.kpi2_paid),
        created_at=rec.created_at.strftime("%d.%m.%Y %H:%M") if rec.created_at else "",
    )


@router.post("/records/latest", response_model=LatestResponse,
             dependencies=[Depends(verify_internal_token)])
def latest_records(payload: LatestRequest, db: Session = Depends(get_db)):
    """Последний расчёт и себестоимость по каждому пользователю и периоду (для dashboard-service)."""
    rec_rows = db.scalars(
        select(PayrollRecord)
        .where(PayrollRecord.user_id.in_(payload.user_ids), PayrollRecord.period.in_(payload.periods))
        .order_by(PayrollRecord.created_at.desc())
    ).all()
    cp_rows = db.scalars(
        select(CostPriceRecord)
        .where(CostPriceRecord.user_id.in_(payload.user_ids), CostPriceRecord.period.in_(payload.periods))
        .order_by(CostPriceRecord.created_at.desc())
    ).all()

    records: Dict[int, Dict[str, Optional[RecordBrief]]] = {
        uid: {p: None for p in payload.periods} for uid in payload.user_ids
    }
    for rec in rec_rows:
        user_map = records.get(rec.user_id)
        if user_map is not None and user_map.get(rec.period) is None:
            user_map[rec.period] = _record_brief(rec)

    cost_prices: Dict[int, Dict[str, float]] = {uid: {} for uid in payload.user_ids}
    for cp in cp_rows:
        user_map = cost_prices.get(cp.user_id)
        if user_map is not None and cp.period not in user_map:
            user_map[cp.period] = float(cp.cost_price)

    return LatestResponse(records=records, cost_prices=cost_prices)
