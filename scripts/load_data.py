import json
from datetime import date, datetime
from pathlib import Path
from sqlalchemy import text
from app.db import engine

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


SCHEMA = """
DROP TABLE IF EXISTS slots, prices, customers, technicians, services,
    categories, vehicle_classes, branches CASCADE;
DROP SEQUENCE IF EXISTS booking_seq;

CREATE TABLE branches (
    branch_id     int PRIMARY KEY,
    code          text UNIQUE NOT NULL,
    name          text NOT NULL,
    city          text NOT NULL,
    state         text NOT NULL,
    timezone      text NOT NULL,
    bays          int NOT NULL,
    open_saturday boolean NOT NULL,
    opened_on     date NOT NULL,
    closed_on     date,
    is_active     boolean NOT NULL
);

CREATE TABLE categories (
    category_id int PRIMARY KEY,
    code        text UNIQUE NOT NULL,
    name        text NOT NULL
);

CREATE TABLE vehicle_classes (
    vehicle_class    text PRIMARY KEY,
    name             text NOT NULL,
    price_multiplier numeric(4, 2) NOT NULL
);

CREATE TABLE services (
    service_id       int PRIMARY KEY,
    code             text UNIQUE NOT NULL,
    name             text NOT NULL,
    category_id      int NOT NULL REFERENCES categories,
    duration_minutes int NOT NULL,
    applies_to       text NOT NULL
);

CREATE TABLE prices (
    price_id       int PRIMARY KEY,
    branch_id      int NOT NULL REFERENCES branches,
    service_id     int NOT NULL REFERENCES services,
    vehicle_class  text NOT NULL REFERENCES vehicle_classes,
    list_price     numeric(8, 2) NOT NULL,
    discount_pct   int,
    effective_from date NOT NULL,
    effective_to   date
);

CREATE TABLE technicians (
    technician_id int PRIMARY KEY,
    branch_id     int NOT NULL REFERENCES branches,
    full_name     text NOT NULL,
    skills        text[] NOT NULL,
    hourly_rate   numeric(5, 2) NOT NULL,
    hired_on      date NOT NULL,
    left_on       date
);

CREATE TABLE customers (
    customer_id    int PRIMARY KEY,
    home_branch_id int NOT NULL REFERENCES branches,
    vehicle_class  text NOT NULL REFERENCES vehicle_classes,
    joined_on      date NOT NULL
);

CREATE TABLE slots (
    slot_id       int PRIMARY KEY,
    branch_id     int NOT NULL REFERENCES branches,
    bay           int NOT NULL,
    start_at      timestamp NOT NULL,
    end_at        timestamp NOT NULL,
    status        text NOT NULL,
    block_reason  text,
    booking_id    text,
    technician_id int REFERENCES technicians,
    customer_id   int REFERENCES customers,
    service_id    int REFERENCES services,
    vehicle_class text REFERENCES vehicle_classes,
    booked_at     timestamp,
    price_quoted  numeric(8, 2),
    rating        int,
    UNIQUE (branch_id, bay, start_at)
);

CREATE INDEX slots_start_at_idx ON slots (start_at);
CREATE INDEX slots_booking_id_idx ON slots (booking_id);
CREATE SEQUENCE booking_seq;
"""

DATE_FIELDS = {"opened_on", "closed_on", "effective_from", "effective_to", "hired_on", "left_on", "joined_on"}
TIMESTAMP_FIELDS = {"start_at", "end_at", "booked_at"}

def convert(row: dict) -> dict:
    out = {}
    for key, value in row.items():
        if value is not None and key in DATE_FIELDS:
            value = date.fromisoformat(value)
        elif value is not None and key in TIMESTAMP_FIELDS:
            value = datetime.fromisoformat(value)
        out[key] = value
    return out

def insert(conn, table: str, rows: list[dict]) -> None:
    columns = list(rows[0])
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(':' + c for c in columns)})"
    conn.execute(text(sql), [convert(r) for r in rows])
    print(f"{table:16} {len(rows):>6} rows")

def main() -> None:
    prices = json.loads((DATA_DIR / "prices.json").read_text(encoding="utf-8"))
    slots = json.loads((DATA_DIR / "slots.json").read_text(encoding="utf-8"))

    with engine.begin() as conn:
        conn.execute(text(SCHEMA))
        insert(conn, "branches", prices["branches"])
        insert(conn, "categories", prices["categories"])
        insert(conn, "vehicle_classes", prices["vehicle_classes"])
        insert(conn, "services", prices["services"])
        insert(conn, "prices", prices["prices"])
        insert(conn, "technicians", slots["technicians"])
        insert(conn, "customers", slots["customers"])
        insert(conn, "slots", slots["slots"])
        conn.execute(text(
            "SELECT setval('booking_seq', (SELECT max(substring(booking_id FROM 4)::int) FROM slots))"
        ))


if __name__ == "__main__":
    main()