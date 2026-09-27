from datetime import date

from langfuse import observe
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.tools.slots import NotFoundError


@observe(name="get_price")
def get_price(
    db: Session,
    service_code: str,
    vehicle_class: str | None = None,
    branch_id: int | None = None,
    on_date: date | None = None,
) -> list[dict]:
    code = service_code.strip().upper()
    on_date = on_date or date.today()

    service = db.execute(
        text("SELECT service_id FROM services WHERE code = :code"), {"code": code}
    ).mappings().first()
    if service is None:
        raise NotFoundError(f"no service with code {code!r}")

    rows = db.execute(
        text("""
            SELECT s.code AS service_code, s.name AS service_name, s.duration_minutes,
                   p.branch_id, b.name AS branch_name, p.vehicle_class,
                   p.list_price, p.discount_pct,
                   round(p.list_price * (1 - coalesce(p.discount_pct, 0) / 100.0), 2) AS price,
                   p.effective_from, p.effective_to
            FROM prices p
            JOIN services s ON s.service_id = p.service_id
            JOIN branches b ON b.branch_id = p.branch_id
            WHERE s.code = :code
              AND p.effective_from <= :on_date
              AND (p.effective_to IS NULL OR p.effective_to >= :on_date)
              AND (CAST(:vehicle_class AS text) IS NULL OR p.vehicle_class = :vehicle_class)
              AND (CAST(:branch_id AS int) IS NULL OR p.branch_id = :branch_id)
            ORDER BY p.branch_id, p.vehicle_class
        """),
        {"code": code, "on_date": on_date, "vehicle_class": vehicle_class, "branch_id": branch_id},
    ).mappings().all()
    return [dict(row) for row in rows]
