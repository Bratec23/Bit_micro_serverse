from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Base
from app.seed import seed


engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


def _migrate() -> None:
    """Лёгкие миграции: добавление новых колонок в существующие таблицы (SQLite/PostgreSQL)."""
    from sqlalchemy import inspect, text

    new_columns = {
        "grades": [
            ("scheme", "VARCHAR(20) NOT NULL DEFAULT 'margin'"),
            ("department_id", "INTEGER"),
            ("kpi2_bonus_type", "VARCHAR(10) NOT NULL DEFAULT 'percent'"),
            ("kpi2_fixed_amount", "NUMERIC(12, 2) NOT NULL DEFAULT 0"),
        ],
    }
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, cols in new_columns.items():
            if table not in insp.get_table_names():
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in cols:
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()