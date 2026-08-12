"""Smoke-тест KPI3 (продажа новых АС, 5%) и его включения в gross."""
import os
import sys
import types
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./smoke_payroll.db")

_pkg_dir = Path(__file__).resolve().parent
_pkg = types.ModuleType("app")
_pkg.__path__ = [str(_pkg_dir)]
sys.modules.setdefault("app", _pkg)

from app.routers.payroll import PayrollCalcIn, _calc, _calc_kpi3, KPI3_AS_RATE

assert KPI3_AS_RATE == 5.0
assert _calc_kpi3(100000) == 5000.0
assert _calc_kpi3(0) == 0.0
assert _calc_kpi3(123456) == round(123456 * 0.05, 2)

p = PayrollCalcIn(
    period="2026-08", worked_days=22, working_days=22, tax_rate=13.0,
    service_revenue=0, goods_revenue=0,
    kpi3_as_revenue=200000,
)

# Без KPI3
c1 = _calc(base_salary=50000, bonus_percent=0, service_factor=1.0, p=p, kpi2_bonus=0, kpi3_bonus=0)
# С KPI3 = 5% от 200000 = 10000
c2 = _calc(base_salary=50000, bonus_percent=0, service_factor=1.0, p=p,
           kpi2_bonus=0, kpi3_bonus=_calc_kpi3(p.kpi3_as_revenue))

assert c2["gross_pay"] - c1["gross_pay"] == 10000.0, (c2["gross_pay"], c1["gross_pay"])
# НДФЛ считается с gross, значит и налог вырос корректно
assert round(c2["tax_amount"] - c1["tax_amount"], 2) == round(10000 * 0.13, 2)
assert c2["net_pay"] > c1["net_pay"]

# KPI3 не влияет на bonus_total (идёт отдельной строкой)
assert c2["bonus_total"] == c1["bonus_total"]

print(f"gross без KPI3={c1['gross_pay']}  с KPI3={c2['gross_pay']}  (премия 10000)")
print("ВСЕ ТЕСТЫ KPI3 ПРОШЛИ")
