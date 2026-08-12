from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class KPDocument(Base):
    __tablename__ = "kp_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Коммерческое предложение")
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    # «Поделиться»: документ виден всем пользователям в общем списке (только чтение)
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
