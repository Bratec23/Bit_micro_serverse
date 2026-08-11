from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Base


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate() -> None:
    """Лёгкие миграции: добавление новых колонок (SQLite/PostgreSQL)."""
    from sqlalchemy import inspect, text

    new_columns = {
        "payroll_records": [
            ("month_margin", "NUMERIC(14, 2) NOT NULL DEFAULT 0"),
            ("scheme", "VARCHAR(20) NOT NULL DEFAULT 'margin'"),
            ("sales_new", "NUMERIC(14, 2) NOT NULL DEFAULT 0"),
            ("sales_expansion", "NUMERIC(14, 2) NOT NULL DEFAULT 0"),
            ("sales_upgrade", "NUMERIC(14, 2) NOT NULL DEFAULT 0"),
            ("sales_renew", "NUMERIC(14, 2) NOT NULL DEFAULT 0"),
            ("sbis_goods", "NUMERIC(14, 2) NOT NULL DEFAULT 0"),
            ("bonus_new", "NUMERIC(14, 2) NOT NULL DEFAULT 0"),
            ("bonus_expansion", "NUMERIC(14, 2) NOT NULL DEFAULT 0"),
            ("bonus_upgrade", "NUMERIC(14, 2) NOT NULL DEFAULT 0"),
            ("bonus_renew", "NUMERIC(14, 2) NOT NULL DEFAULT 0"),
            ("bonus_sbis_goods", "NUMERIC(14, 2) NOT NULL DEFAULT 0"),
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
