from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    positions: Mapped[list["Position"]] = relationship("Position", back_populates="department", cascade="all, delete-orphan")
    users: Mapped[list["User"]] = relationship("User", back_populates="department")


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    department: Mapped["Department"] = relationship("Department", back_populates="positions")
    users: Mapped[list["User"]] = relationship("User", back_populates="position")


class Grade(Base):
    __tablename__ = "grades"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_salary: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    bonus_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    service_factor: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0.5)
    has_plan: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    plan_margin: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True, default=None)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    kpi2_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    kpi2_bonus_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=5.0)
    kpi2_min_retention_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=80.0)
    # схема мотивации: "margin" (маржа АРТ) | "abt" (реализация СБИС)
    scheme: Mapped[str] = mapped_column(String(20), nullable=False, default="margin")
    # отдел, которому принадлежит грейд (None = общий, legacy)
    department_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    # KPI2: "percent" (% от прихода) | "fixed" (фиксированная сумма)
    kpi2_bonus_type: Mapped[str] = mapped_column(String(10), nullable=False, default="percent")
    kpi2_fixed_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    users: Mapped[list["User"]] = relationship("User", back_populates="grade")
    tiers: Mapped[list["GradeTier"]] = relationship("GradeTier", back_populates="grade", cascade="all, delete-orphan", order_by="GradeTier.min_pct")


class GradeTier(Base):
    __tablename__ = "grade_tiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    grade_id: Mapped[str] = mapped_column(String(50), ForeignKey("grades.id", ondelete="CASCADE"), index=True, nullable=False)
    min_pct: Mapped[float] = mapped_column(Numeric(7, 2), nullable=False, default=0)
    bonus_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)

    grade: Mapped["Grade"] = relationship("Grade", back_populates="tiers")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="manager")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey("departments.id"), index=True, nullable=False)
    position_id: Mapped[int] = mapped_column(Integer, ForeignKey("positions.id"), nullable=False)
    grade_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("grades.id"), nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    department: Mapped["Department"] = relationship("Department", back_populates="users")
    position: Mapped["Position"] = relationship("Position", back_populates="users")
    grade: Mapped["Grade | None"] = relationship("Grade", back_populates="users")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User")


class LoginAudit(Base):
    __tablename__ = "login_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ip: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    user_agent: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    detail: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)