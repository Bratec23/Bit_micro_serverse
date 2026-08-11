"""Smoke-тест логики расчёта АБТ (без запуска сервисов)."""
import os
import sys
import types
from pathlib import Path

# До импорта модулей сервиса: локальная SQLite вместо Postgres.
os.environ.setdefault("DATABASE_URL", "sqlite:///./smoke_payroll.db")

# Регистрируем директорию сервиса как пакет "app" (как делает run_server.py),
# чтобы работали импорты вида "from app.routers.payroll import ...".
_pkg_dir = Path(__file__).resolve().parent
_pkg = types.ModuleType("app")
_pkg.__path__ = [str(_pkg_dir)]
sys.modules.setdefault("app", _pkg)

from app.routers.payroll import PayrollCalcIn, _abt_rates, _calc_abt, _calc_kpi2

GRADE = {
    "id": "abt_mgr", "name": "Менеджер отдела Сопровождения",
    "base_salary": 40000, "has_plan": True, "plan_margin": 500000,
    "kpi2_enabled": True, "kpi2_bonus_type": "fixed",
    "kpi2_fixed_amount": 5000, "kpi2_min_retention_pct": 83.0,
}


def make_in(**kw):
    base = dict(period="2026-08", worked_days=22, working_days=22, tax_rate=13.0,
                kpi2_retention_pct=85.0)
    base.update(kw)
    return PayrollCalcIn(**base)


def show(title, calc):
    print(f"--- {title}")
    print(f"  оклад={calc['accrued_base']}  премии: new={calc['bonus_new']} exp={calc['bonus_expansion']} "
          f"upg={calc['bonus_upgrade']} ren={calc['bonus_renew']} sbis={calc['bonus_sbis_goods']}")
    print(f"  bonus_total={calc['bonus_total']}  gross={calc['gross_pay']}  ndfl={calc['tax_amount']}  net={calc['net_pay']}")


# KPI2 fixed
b, paid = _calc_kpi2(GRADE, 0, 85.0)
assert (b, paid) == (5000.0, True), (b, paid)
b, paid = _calc_kpi2(GRADE, 0, 80.0)
assert (b, paid) == (0.0, False), (b, paid)
print("KPI2 fixed OK")

# 80% плана -> колонка 0 (8/7/5/1.2)
p = make_in(sales_new=200000, sales_expansion=100000, sales_upgrade=50000, sales_renew=50000, sbis_goods=100000)
kpi2, _ = _calc_kpi2(GRADE, 0, p.kpi2_retention_pct)
c = _calc_abt(GRADE, p, kpi2)
show("80% плана, колонка 0", c)
assert c["performance_pct"] == 80.0
assert c["bonus_new"] == 16000.0 and c["bonus_expansion"] == 7000.0
assert c["bonus_upgrade"] == 2500.0 and c["bonus_renew"] == 600.0
assert c["bonus_sbis_goods"] == 10000.0 and c["bonus_total"] == 36100.0
assert c["gross_pay"] == 40000.0 + 36100.0 + 5000.0

# 95% -> колонка 1 (10/9/7/1.3)
p = make_in(sales_new=300000, sales_expansion=100000, sales_upgrade=50000, sales_renew=25000)
c = _calc_abt(GRADE, p, 0)
show("95% плана, колонка 1", c)
assert c["performance_pct"] == 95.0
assert c["bonus_new"] == 30000.0 and c["bonus_expansion"] == 9000.0
assert c["bonus_upgrade"] == 3500.0 and c["bonus_renew"] == 325.0

# 115% -> new=15, остальные колонка 2 (11/9/1.5)
p = make_in(sales_new=400000, sales_expansion=100000, sales_upgrade=50000, sales_renew=25000)
c = _calc_abt(GRADE, p, 0)
show("115% плана, перевыполнение", c)
assert c["performance_pct"] == 115.0
assert c["bonus_new"] == 60000.0 and c["bonus_expansion"] == 11000.0
assert c["bonus_upgrade"] == 4500.0 and c["bonus_renew"] == 375.0

# 135% -> new=20
p = make_in(sales_new=600000, sales_expansion=50000, sales_upgrade=20000, sales_renew=5000)
c = _calc_abt(GRADE, p, 0)
show("135% плана", c)
assert c["performance_pct"] == 135.0
assert c["bonus_new"] == 120000.0 and c["bonus_expansion"] == 5500.0

# без плана -> базовая колонка 0
g2 = dict(GRADE, has_plan=False, plan_margin=None)
p = make_in(sales_new=100000, sales_expansion=0, sales_upgrade=0, sales_renew=0)
c = _calc_abt(g2, p, 0)
show("без плана (испытательный)", c)
assert c["performance_pct"] is None and c["bonus_new"] == 8000.0

print("\nВСЕ ТЕСТЫ ПРОШЛИ")
