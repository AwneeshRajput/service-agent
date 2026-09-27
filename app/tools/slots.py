from datetime import date, datetime, timedelta
from math import ceil

from langfuse import observe
from langfuse import observe
from sqlalchemy import text
from sqlalchemy.orm import Session

class NotFoundError(Exception):
    pass

class BookingError(Exception):
    pass

@observe(name="get_free_slots")
def get_free_slots(db: Session, day: date, branch_id: int | None = None) -> list[dict]:
    rows = db.execute(
        text("""
            SELECT s.slot_id, s.branch_id, b.name AS branch_name, s.bay, s.start_at, s.end_at
            FROM slots s
            JOIN branches b ON b.branch_id = s.branch_id
            WHERE s.status = 'available'
              AND s.start_at >= :day_start
              AND s.start_at <  :day_end
              AND (CAST(:branch_id AS int) IS NULL OR s.branch_id = :branch_id)
            ORDER BY s.start_at, s.branch_id, s.bay
        """),
        {"day_start": day, "day_end": day + timedelta(days=1), "branch_id": branch_id},
    ).mappings().all()
    return [dict(row) for row in rows]



@observe(name="book_slot")
def book_slot(db: Session, slot_id: int, customer_id: int, service_id: int) -> dict:
    first = db.execute(
        text("SELECT slot_id, branch_id, bay, start_at, status FROM slots WHERE slot_id = :id FOR UPDATE"),
        {"id": slot_id},
    ).mappings().first() 
    if first is None:
        raise NotFoundError(f"slot {slot_id} does not exist")
    if first["status"] != "available":
        raise BookingError(f"slot {slot_id} is {first['status']}, not available")
    if first["start_at"] <= datetime.now():
        raise BookingError(f"slot {slot_id} starts in the past")
    
    customer = db.execute(
        text("SELECT customer_id, vehicle_class FROM customers WHERE customer_id = :id"),
        {"id": customer_id},
    ).mappings().first()
    if customer is None:
        raise NotFoundError(f"customer {customer_id} does not exist")

    service = db.execute(
        text("""
            SELECT s.service_id, s.duration_minutes, c.code AS category
            FROM services s JOIN categories c ON c.category_id = s.category_id
            WHERE s.service_id = :id
        """),
        {"id": service_id},
    ).mappings().first()
    if service is None:
        raise NotFoundError(f"service {service_id} does not exist")

    hours_needed = ceil(service["duration_minutes"] / 60)
    start = first["start_at"]
    end = start + timedelta(hours=hours_needed)

    block = db.execute(
        text("""
            SELECT slot_id, status FROM slots
            WHERE branch_id = :branch_id AND bay = :bay
              AND start_at >= :start AND start_at < :end
            ORDER BY start_at
            FOR UPDATE
        """),
        {"branch_id": first["branch_id"], "bay": first["bay"], "start": start, "end": end},
    ).mappings().all()
    if len(block) < hours_needed or any(s["status"] != "available" for s in block):
        raise BookingError(f"this service needs {hours_needed} free consecutive hour(s) in the same bay")

    price = db.execute(
        text("""
            SELECT round(list_price * (1 - coalesce(discount_pct, 0) / 100.0), 2) AS quoted
            FROM prices
            WHERE branch_id = :branch_id AND service_id = :service_id AND vehicle_class = :vehicle_class
              AND effective_from <= CURRENT_DATE
              AND (effective_to IS NULL OR effective_to >= CURRENT_DATE)
        """),
        {"branch_id": first["branch_id"], "service_id": service_id, "vehicle_class": customer["vehicle_class"]},
    ).scalar()
    if price is None:
        raise BookingError("this branch does not offer that service for the customer's vehicle")

    technician_id = db.execute(
        text("""
            SELECT t.technician_id
            FROM technicians t
            WHERE t.branch_id = :branch_id
              AND :category = ANY(t.skills)
              AND t.hired_on <= :day
              AND (t.left_on IS NULL OR t.left_on >= :day)
              AND NOT EXISTS (
                  SELECT 1 FROM slots s
                  WHERE s.technician_id = t.technician_id
                    AND s.status IN ('booked', 'in_progress')
                    AND s.start_at >= :start AND s.start_at < :end
              )
            ORDER BY t.technician_id
            LIMIT 1
        """),
        {"branch_id": first["branch_id"], "category": service["category"],
         "day": start.date(), "start": start, "end": end},
    ).scalar()
    if technician_id is None:
        raise BookingError("no qualified technician is free at that time")

    booking_id = db.execute(text("SELECT 'BK-' || lpad(nextval('booking_seq')::text, 6, '0')")).scalar()
    db.execute(
        text("""
            UPDATE slots
            SET status = 'booked', booking_id = :booking_id, technician_id = :technician_id,
                customer_id = :customer_id, service_id = :service_id, vehicle_class = :vehicle_class,
                booked_at = LOCALTIMESTAMP(0), price_quoted = :price
            WHERE slot_id = ANY(:slot_ids)
        """),
        {"booking_id": booking_id, "technician_id": technician_id, "customer_id": customer_id,
         "service_id": service_id, "vehicle_class": customer["vehicle_class"], "price": price,
         "slot_ids": [s["slot_id"] for s in block]},
    )
    db.commit()

    return {
        "booking_id": booking_id,
        "branch_id": first["branch_id"],
        "bay": first["bay"],
        "start_at": start,
        "end_at": end,
        "service_id": service_id,
        "customer_id": customer_id,
        "technician_id": technician_id,
        "price_quoted": price,
        "status": "booked",
    }