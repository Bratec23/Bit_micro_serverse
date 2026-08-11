from sqlalchemy.orm import Session

from app.models import Department, Grade, GradeTier, Position


GRADES_SEED = [
    {
        "id": "trainee",
        "name": "Испытательный срок",
        "base_salary": 45000,
        "bonus_percent": 4.0,
        "service_factor": 0.5,
        "has_plan": False,
        "plan_margin": None,
        "sort_order": 1,
        "kpi2_enabled": False,
        "tiers": [],
    },
    {
        "id": "mgr1",
        "name": "Менеджер по продажам, 1 грейд",
        "base_salary": 37500,
        "bonus_percent": 0.0,
        "service_factor": 0.5,
        "has_plan": True,
        "plan_margin": 230000,
        "kpi2_enabled": True,
        "sort_order": 2,
        "tiers": [(0, 0), (90, 4), (101, 5), (130, 6), (150, 7), (200, 9)],
    },
    {
        "id": "mgr2",
        "name": "Менеджер по продажам, 2 грейд",
        "base_salary": 37500,
        "bonus_percent": 0.0,
        "service_factor": 0.5,
        "has_plan": True,
        "plan_margin": 300000,
        "kpi2_enabled": True,
        "sort_order": 3,
        "tiers": [(0, 0), (90, 5), (101, 6), (130, 7), (150, 8), (200, 10)],
    },
    {
        "id": "lead1",
        "name": "Ведущий менеджер, 1 грейд",
        "base_salary": 42000,
        "bonus_percent": 0.0,
        "service_factor": 0.5,
        "has_plan": True,
        "plan_margin": 370000,
        "kpi2_enabled": True,
        "sort_order": 4,
        "tiers": [(0, 0), (90, 3), (101, 6), (130, 10), (150, 12), (200, 14)],
    },
    {
        "id": "lead2",
        "name": "Ведущий менеджер, 2 грейд",
        "base_salary": 50000,
        "bonus_percent": 0.0,
        "service_factor": 0.5,
        "has_plan": True,
        "plan_margin": 420000,
        "kpi2_enabled": True,
        "sort_order": 5,
        "tiers": [(0, 0), (90, 3), (101, 5), (130, 10), (150, 12), (200, 14)],
    },
]


ABT_GRADES_SEED = [
    {
        "id": "abt_trainee",
        "name": "Испытательный срок",
        "base_salary": 40000,
        "bonus_percent": 0.0,
        "service_factor": 0.5,
        "has_plan": False,
        "plan_margin": None,
        "sort_order": 1,
        "kpi2_enabled": True,
        "kpi2_bonus_type": "fixed",
        "kpi2_fixed_amount": 5000,
        "kpi2_min_retention_pct": 83.0,
        "scheme": "abt",
        "tiers": [],
    },
    {
        "id": "abt_mgr",
        "name": "Менеджер отдела Сопровождения",
        "base_salary": 40000,
        "bonus_percent": 0.0,
        "service_factor": 0.5,
        "has_plan": True,
        "plan_margin": 500000,
        "sort_order": 2,
        "kpi2_enabled": True,
        "kpi2_bonus_type": "fixed",
        "kpi2_fixed_amount": 5000,
        "kpi2_min_retention_pct": 83.0,
        "scheme": "abt",
        "tiers": [],
    },
]


def _create_grade(db: Session, g: dict, department_id: int | None) -> None:
    tiers_data = g.get("tiers", [])
    grade_data = {k: v for k, v in g.items() if k != "tiers"}
    grade = Grade(**grade_data, is_active=True, department_id=department_id)
    db.add(grade)
    db.flush()
    for min_pct, bonus_pct in tiers_data:
        db.add(GradeTier(grade_id=grade.id, min_pct=min_pct, bonus_percent=bonus_pct))


def seed(db: Session) -> None:
    if not db.query(Department).first():
        db.add(Department(code="dev_art", name="Отдел развитие АРТ", is_active=True))
        db.add(Department(code="maintenance", name="Отдел Сопровождение", is_active=True))
        db.flush()

    # отдел АБТ (идемпотентно)
    abt = db.query(Department).filter(Department.code == "abt").first()
    if not abt:
        abt = Department(code="abt", name="Отдел АБТ", is_active=True)
        db.add(abt)
        db.flush()

    if not db.query(Position).first():
        dev = db.query(Department).filter(Department.code == "dev_art").first()
        mnt = db.query(Department).filter(Department.code == "maintenance").first()
        if dev:
            db.add(Position(name="Менеджер отдела развитие АРТ", department_id=dev.id, is_active=True))
            db.add(Position(name="Руководитель отдела развитие АРТ", department_id=dev.id, is_active=True))
        if mnt:
            db.add(Position(name="Специалист сопровождения", department_id=mnt.id, is_active=True))
        db.flush()

    # должности АБТ (идемпотентно)
    existing_abt_pos = {p.name for p in db.query(Position).filter(Position.department_id == abt.id).all()}
    if "Менеджер АБТ" not in existing_abt_pos:
        db.add(Position(name="Менеджер АБТ", department_id=abt.id, is_active=True))
    if "Руководитель АБТ" not in existing_abt_pos:
        db.add(Position(name="Руководитель АБТ", department_id=abt.id, is_active=True))
    db.flush()

    if not db.query(Grade).first():
        dev = db.query(Department).filter(Department.code == "dev_art").first()
        for g in GRADES_SEED:
            _create_grade(db, g, dev.id if dev else None)
        db.flush()
    else:
        for g in GRADES_SEED:
            existing = db.get(Grade, g["id"])
            if existing:
                existing.sort_order = g["sort_order"]
        # привязываем legacy-грейды без отдела к отделу АРТ
        dev = db.query(Department).filter(Department.code == "dev_art").first()
        if dev:
            legacy_ids = [g["id"] for g in GRADES_SEED]
            for grade in db.query(Grade).filter(Grade.department_id.is_(None)).all():
                if grade.id in legacy_ids:
                    grade.department_id = dev.id
        db.flush()

    # грейды АБТ (идемпотентно)
    for g in ABT_GRADES_SEED:
        if not db.get(Grade, g["id"]):
            _create_grade(db, g, abt.id)
    db.flush()

    db.commit()
