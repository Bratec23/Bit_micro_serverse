from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PayrollRecord(Base):
    __tablename__ = "payroll_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    worked_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    working_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    service_margin: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    goods_margin: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    # маржа за месяц — отдельный показатель для выполнения плана и ступеней (АРТ)
    month_margin: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    bonus_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    service_factor: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0.5)
    base_salary: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    accrued_base: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    services_bonus: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    goods_bonus: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    bonus_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=13.0)
    gross_pay: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    net_pay: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    grade_id: Mapped[str] = mapped_column(String(50), nullable=False)
    grade_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    has_plan: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    plan_margin: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True, default=None)
    margin_for_plan: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    performance_pct: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True, default=None)
    kpi2_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    kpi2_revenue: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    kpi2_retention_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    kpi2_bonus_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    kpi2_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    grade_kpi2_bonus_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=5.0)
    grade_kpi2_min_retention_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=80.0)
    # KPI3 (АРТ): приход с новых АС — премия 5% от суммы, суммы вносятся без НДС
    kpi3_as_revenue: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    kpi3_bonus_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    # схема мотивации: "margin" (маржа АРТ) | "abt" (реализация СБИС)
    scheme: Mapped[str] = mapped_column(String(20), nullable=False, default="margin")
    # АБТ: реализация по типам продаж
    sales_new: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    sales_expansion: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    sales_upgrade: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    sales_renew: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    sbis_goods: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    # АБТ: премии по типам продаж
    bonus_new: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    bonus_expansion: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    bonus_upgrade: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    bonus_renew: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    bonus_sbis_goods: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CostPriceRecord(Base):
    __tablename__ = "cost_price_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    cost_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
