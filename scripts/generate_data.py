"""Generate synthetic data/prices.json and data/slots.json. Same seed, same output."""

import json
import math
import random
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

SEED = 42
AS_OF = datetime(2026, 9, 22, 9, 0)
WINDOW_START = date(2026, 7, 1)
WINDOW_END = date(2026, 11, 30)
PRICE_HISTORY_START = date(2025, 1, 1)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

rng = random.Random(SEED)

BRANCHES = [
    {"branch_id": 1, "code": "SEA", "name": "Seattle Downtown", "city": "Seattle", "state": "WA", "timezone": "America/Los_Angeles", "bays": 5, "open_saturday": True, "opened_on": "2019-03-12", "closed_on": None, "is_active": True},
    {"branch_id": 2, "code": "PDX", "name": "Portland East", "city": "Portland", "state": "OR", "timezone": "America/Los_Angeles", "bays": 4, "open_saturday": False, "opened_on": "2020-06-01", "closed_on": None, "is_active": True},
    {"branch_id": 3, "code": "DEN", "name": "Denver Central", "city": "Denver", "state": "CO", "timezone": "America/Denver", "bays": 4, "open_saturday": True, "opened_on": "2018-09-15", "closed_on": None, "is_active": True},
    {"branch_id": 4, "code": "AUS", "name": "Austin North", "city": "Austin", "state": "TX", "timezone": "America/Chicago", "bays": 5, "open_saturday": True, "opened_on": "2021-02-08", "closed_on": None, "is_active": True},
    {"branch_id": 5, "code": "CHI", "name": "Chicago Loop", "city": "Chicago", "state": "IL", "timezone": "America/Chicago", "bays": 6, "open_saturday": True, "opened_on": "2017-11-20", "closed_on": None, "is_active": True},
    {"branch_id": 6, "code": "ATL", "name": "Atlanta Midtown", "city": "Atlanta", "state": "GA", "timezone": "America/New_York", "bays": 3, "open_saturday": False, "opened_on": "2023-05-02", "closed_on": None, "is_active": True},
    {"branch_id": 7, "code": "BOS", "name": "Boston Back Bay", "city": "Boston", "state": "MA", "timezone": "America/New_York", "bays": 3, "open_saturday": False, "opened_on": "2016-04-18", "closed_on": "2025-12-31", "is_active": False},
]
PRICE_FACTOR = {1: 1.10, 2: 1.02, 3: 1.00, 4: 0.97, 5: 1.08, 6: 0.94, 7: 1.12}
DEMAND = {1: 0.60, 2: 0.46, 3: 0.50, 4: 0.56, 5: 0.64, 6: 0.40}

CATEGORIES = [
    {"category_id": 1, "code": "MNT", "name": "Maintenance"},
    {"category_id": 2, "code": "BRK", "name": "Brakes"},
    {"category_id": 3, "code": "TYR", "name": "Tyres"},
    {"category_id": 4, "code": "ENG", "name": "Engine"},
    {"category_id": 5, "code": "ELC", "name": "Electrical"},
    {"category_id": 6, "code": "CLM", "name": "Climate Control"},
    {"category_id": 7, "code": "DTL", "name": "Detailing"},
]
CATEGORY_ID = {c["code"]: c["category_id"] for c in CATEGORIES}

# code, name, category, minutes, base price (hatchback), popularity weight, applies_to
SERVICE_ROWS = [
    ("OIL", "Oil & Filter Change", "MNT", 45, 59, 30, "combustion"),
    ("SYN", "Full Synthetic Oil Change", "MNT", 45, 89, 18, "combustion"),
    ("BSV", "Basic Service", "MNT", 90, 149, 14, "all"),
    ("MSV", "Major Service", "MNT", 180, 349, 6, "all"),
    ("AIR", "Engine Air Filter Replacement", "MNT", 20, 35, 8, "combustion"),
    ("CAB", "Cabin Air Filter Replacement", "MNT", 20, 39, 8, "all"),
    ("CLT", "Coolant Flush", "MNT", 60, 99, 5, "all"),
    ("TRN", "Transmission Fluid Change", "MNT", 60, 139, 4, "combustion"),
    ("BPF", "Front Brake Pads", "BRK", 90, 179, 9, "all"),
    ("BPR", "Rear Brake Pads", "BRK", 90, 169, 6, "all"),
    ("BDR", "Brake Disc Replacement (pair)", "BRK", 120, 289, 3, "all"),
    ("BFL", "Brake Fluid Flush", "BRK", 45, 79, 5, "all"),
    ("BIN", "Brake Inspection", "BRK", 30, 29, 10, "all"),
    ("ROT", "Tyre Rotation", "TYR", 30, 25, 20, "all"),
    ("ALN", "Wheel Alignment", "TYR", 60, 89, 12, "all"),
    ("BAL", "Wheel Balancing (set of 4)", "TYR", 45, 49, 9, "all"),
    ("PUN", "Puncture Repair", "TYR", 30, 29, 10, "all"),
    ("TFT", "Tyre Fitting (per tyre)", "TYR", 30, 22, 11, "all"),
    ("DIA", "Engine Diagnostic Scan", "ENG", 45, 79, 10, "combustion"),
    ("SPK", "Spark Plug Replacement", "ENG", 60, 119, 4, "combustion"),
    ("TBL", "Timing Belt Replacement", "ENG", 240, 549, 2, "combustion"),
    ("FIC", "Fuel Injector Cleaning", "ENG", 90, 159, 3, "combustion"),
    ("EXH", "Exhaust Repair", "ENG", 120, 229, 3, "combustion"),
    ("BAT", "12V Battery Replacement", "ELC", 30, 169, 7, "all"),
    ("ALT", "Alternator Replacement", "ELC", 180, 449, 2, "combustion"),
    ("STR", "Starter Motor Replacement", "ELC", 150, 389, 2, "combustion"),
    ("HLB", "Headlight Bulb Replacement", "ELC", 20, 29, 6, "all"),
    ("EVB", "EV Battery Health Check", "ELC", 60, 129, 8, "electric"),
    ("EVC", "EV Charging Port Repair", "ELC", 120, 279, 3, "electric"),
    ("HVI", "High-Voltage System Inspection", "ELC", 90, 199, 5, "electric"),
    ("ACR", "A/C Regas", "CLM", 60, 109, 7, "all"),
    ("ACD", "A/C Diagnostic", "CLM", 45, 69, 4, "all"),
    ("WAX", "Exterior Wash & Wax", "DTL", 60, 69, 8, "all"),
    ("INT", "Interior Deep Clean", "DTL", 120, 149, 5, "all"),
    ("FDT", "Full Detail", "DTL", 240, 299, 3, "all"),
    ("CER", "Ceramic Coating", "DTL", 480, 899, 1, "all"),
]
SERVICES = [
    {"service_id": i, "code": code, "name": name, "category_id": CATEGORY_ID[cat], "duration_minutes": minutes, "applies_to": applies}
    for i, (code, name, cat, minutes, _, _, applies) in enumerate(SERVICE_ROWS, start=1)
]
BASE_PRICE = {i: row[4] for i, row in enumerate(SERVICE_ROWS, start=1)}
POPULARITY = {i: row[5] for i, row in enumerate(SERVICE_ROWS, start=1)}
CATEGORY_CODE = {i: row[2] for i, row in enumerate(SERVICE_ROWS, start=1)}

VEHICLE_CLASSES = [
    {"vehicle_class": "hatchback", "name": "Hatchback", "price_multiplier": 1.00},
    {"vehicle_class": "sedan", "name": "Sedan", "price_multiplier": 1.15},
    {"vehicle_class": "suv", "name": "SUV", "price_multiplier": 1.35},
    {"vehicle_class": "ev", "name": "Electric Vehicle", "price_multiplier": 1.10},
]

INTRODUCED = {"CER": date(2025, 7, 1), "EVC": date(2026, 3, 1)}
DISCONTINUED = {(2, "FIC"): date(2026, 8, 31)}
NOT_OFFERED = {(6, "TBL"), (6, "ALT")}
DETAILING_BRANCHES = {1, 4, 5, 6}
EV_SERVICE_BRANCHES = {1, 2, 4, 5}
# effective date, increase range, branches (None = all)
PRICE_REVISIONS = [
    (date(2025, 7, 1), (0.03, 0.06), None),
    (date(2026, 1, 1), (0.02, 0.05), None),
    (date(2026, 10, 1), (0.04, 0.07), {1, 3, 5}),
]

HOLIDAYS = {date(2026, 7, 3), date(2026, 9, 7), date(2026, 11, 26)}
DOW_FACTOR = {0: 1.15, 1: 1.0, 2: 0.95, 3: 1.0, 4: 1.1, 5: 1.2}

FIRST_NAMES = ["Alex", "Jordan", "Sam", "Taylor", "Morgan", "Casey", "Riley", "Jamie", "Avery", "Quinn", "Drew", "Reese", "Cameron", "Rowan", "Parker", "Hayden", "Emerson", "Skyler", "Dakota", "Finley", "Marisol", "Tomas", "Priya", "Kenji", "Amara", "Luca", "Ines", "Omar", "Hana", "Mateo"]
LAST_NAMES = ["Nguyen", "Garcia", "Okafor", "Patel", "Kowalski", "Silva", "Haddad", "Johansson", "Tanaka", "Murphy", "Reyes", "Novak", "Adeyemi", "Fischer", "Moreau", "Costa", "Kim", "Larsen", "Mendes", "Brooks"]


def money(value: float) -> float:
    return round(math.ceil(value) - 0.01, 2)


def is_offered(branch_id: int, service: dict, vehicle_class: str) -> bool:
    applies = service["applies_to"]
    if applies == "combustion" and vehicle_class == "ev":
        return False
    if applies == "electric" and (vehicle_class != "ev" or branch_id not in EV_SERVICE_BRANCHES):
        return False
    if CATEGORY_CODE[service["service_id"]] == "DTL" and branch_id not in DETAILING_BRANCHES:
        return False
    return (branch_id, service["code"]) not in NOT_OFFERED


def build_prices() -> list[dict]:
    rows = []
    for branch in BRANCHES:
        bid = branch["branch_id"]
        closed = date.fromisoformat(branch["closed_on"]) if branch["closed_on"] else None
        for service in SERVICES:
            for vc in VEHICLE_CLASSES:
                if not is_offered(bid, service, vc["vehicle_class"]):
                    continue
                start = max(PRICE_HISTORY_START, INTRODUCED.get(service["code"], PRICE_HISTORY_START))
                end = closed or DISCONTINUED.get((bid, service["code"]))
                price = BASE_PRICE[service["service_id"]] * vc["price_multiplier"] * PRICE_FACTOR[bid] * rng.uniform(0.97, 1.03)
                segments = [(start, price)]
                for effective, (lo, hi), only in PRICE_REVISIONS:
                    if effective <= start or (only and bid not in only) or (end and effective > end):
                        continue
                    price *= 1 + rng.uniform(lo, hi)
                    segments.append((effective, price))
                for i, (effective_from, value) in enumerate(segments):
                    effective_to = segments[i + 1][0] - timedelta(days=1) if i + 1 < len(segments) else end
                    rows.append({
                        "price_id": len(rows) + 1,
                        "branch_id": bid,
                        "service_id": service["service_id"],
                        "vehicle_class": vc["vehicle_class"],
                        "list_price": money(value),
                        "discount_pct": rng.choice([10, 15, 20]) if rng.random() < 0.07 else None,
                        "effective_from": effective_from.isoformat(),
                        "effective_to": effective_to.isoformat() if effective_to else None,
                    })
    return rows


def build_technicians() -> list[dict]:
    names = [f"{f} {l}" for f in FIRST_NAMES for l in LAST_NAMES]
    rng.shuffle(names)
    technicians = []
    for branch in BRANCHES:
        if not branch["is_active"]:
            continue
        bid = branch["branch_id"]
        optional = ["BRK", "ENG", "ELC", "CLM"] + (["DTL"] if bid in DETAILING_BRANCHES else [])
        staff = []
        for _ in range(branch["bays"] + 1):
            skills = {"MNT", "TYR"} | set(rng.sample(optional, k=rng.randint(1, 3)))
            hired = date.fromisoformat(branch["opened_on"]) + timedelta(days=rng.randint(0, 900))
            staff.append({
                "technician_id": len(technicians) + len(staff) + 1,
                "branch_id": bid,
                "full_name": names.pop(),
                "skills": skills,
                "hourly_rate": rng.randint(28, 52) + rng.choice([0, 0.5]),
                "hired_on": min(hired, date(2026, 6, 30)),
                "left_on": None,
            })
        for code in optional:
            if not any(code in t["skills"] for t in staff):
                rng.choice(staff)["skills"].add(code)
        technicians.extend(staff)

    by_branch = defaultdict(list)
    for t in technicians:
        by_branch[t["branch_id"]].append(t)
    by_branch[4][-1]["hired_on"] = date(2026, 9, 1)
    by_branch[5][-1]["left_on"] = date(2026, 8, 14)
    return technicians


def build_customers() -> list[dict]:
    active = [b["branch_id"] for b in BRANCHES if b["is_active"]]
    customers = []
    for cid in range(1, 4001):
        customers.append({
            "customer_id": cid,
            "home_branch_id": rng.choices(active, weights=[DEMAND[b] for b in active])[0],
            "vehicle_class": rng.choices(["hatchback", "sedan", "suv", "ev"], weights=[25, 35, 30, 10])[0],
            "joined_on": (date(2018, 1, 1) + timedelta(days=rng.randint(0, 3040))).isoformat(),
            "_activity": rng.paretovariate(1.5),
        })
    return customers


def main() -> None:
    prices = build_prices()
    technicians = build_technicians()
    customers = build_customers()

    price_index = defaultdict(list)
    for p in prices:
        price_index[(p["branch_id"], p["service_id"], p["vehicle_class"])].append(p)

    def price_on(bid: int, sid: int, vc: str, day: date) -> dict | None:
        iso = day.isoformat()
        for p in price_index.get((bid, sid, vc), []):
            if p["effective_from"] <= iso and (p["effective_to"] is None or iso <= p["effective_to"]):
                return p
        return None

    home_pool = defaultdict(list)
    for c in customers:
        home_pool[c["home_branch_id"]].append(c)

    def pick_customer(bid: int) -> dict:
        pool = home_pool[bid] if rng.random() < 0.85 else customers
        return rng.choices(pool, weights=[c["_activity"] for c in pool])[0]

    def pick_booked_at(start: datetime) -> datetime:
        if start > AS_OF:
            return AS_OF - timedelta(minutes=rng.randint(30, 60 * 24 * 21))
        lead = min(60 * 24 * 60, max(120, int(rng.expovariate(1 / (60 * 24 * 5)))))
        return start - timedelta(minutes=lead)

    def hours_for(day: date, branch: dict) -> list[int]:
        wd = day.weekday()
        if wd == 6 or (wd == 5 and not branch["open_saturday"]):
            return []
        return list(range(9, 13)) if wd == 5 else list(range(8, 17))

    active_branches = [b for b in BRANCHES if b["is_active"]]
    training = set()
    for branch in active_branches:
        for month in range(WINDOW_START.month, WINDOW_END.month + 1):
            while True:
                day = date(2026, month, rng.randint(1, 28))
                if day.weekday() < 5 and day not in HOLIDAYS:
                    training.add((branch["branch_id"], day))
                    break

    slots = []
    tech_busy = defaultdict(set)
    booking_seq = 0

    def empty_slot(bid, bay, start, status, block_reason=None):
        return {
            "branch_id": bid, "bay": bay,
            "start_at": start.isoformat(), "end_at": (start + timedelta(hours=1)).isoformat(),
            "status": status, "block_reason": block_reason,
            "booking_id": None, "technician_id": None, "customer_id": None, "service_id": None,
            "vehicle_class": None, "booked_at": None, "price_quoted": None, "rating": None,
        }

    for branch in active_branches:
        bid = branch["branch_id"]
        staff = [t for t in technicians if t["branch_id"] == bid]
        day = WINDOW_START
        while day <= WINDOW_END:
            hours = hours_for(day, branch)
            for bay in range(1, branch["bays"] + 1) if hours else []:
                if day in HOLIDAYS:
                    blocked = {h: "public_holiday" for h in hours}
                elif rng.random() < 0.012:
                    blocked = {h: "bay_maintenance" for h in hours}
                elif (bid, day) in training:
                    blocked = {h: "staff_training" for h in hours if h >= 13}
                else:
                    blocked = {}

                i = 0
                while i < len(hours):
                    start = datetime.combine(day, time(hours[i]))
                    idle = "available" if start > AS_OF else "unused"
                    if hours[i] in blocked:
                        slots.append(empty_slot(bid, bay, start, "blocked", blocked[hours[i]]))
                        i += 1
                        continue

                    hour_factor = 1.15 if hours[i] < 11 else (1.0 if hours[i] < 14 else 0.85)
                    ahead = max(0.0, (start - AS_OF).total_seconds() / 86400)
                    p = DEMAND[bid] * DOW_FACTOR[day.weekday()] * hour_factor * max(0.04, math.exp(-ahead / 21))
                    if rng.random() >= p:
                        slots.append(empty_slot(bid, bay, start, idle))
                        i += 1
                        continue

                    free_run = 0
                    while i + free_run < len(hours) and hours[i + free_run] not in blocked:
                        free_run += 1
                    customer = pick_customer(bid)
                    vc = customer["vehicle_class"]
                    booked_at = pick_booked_at(start)
                    options = [
                        s for s in SERVICES
                        if math.ceil(s["duration_minutes"] / 60) <= free_run
                        and price_on(bid, s["service_id"], vc, booked_at.date())
                        and price_on(bid, s["service_id"], vc, day)
                    ]
                    if not options:
                        slots.append(empty_slot(bid, bay, start, idle))
                        i += 1
                        continue
                    service = rng.choices(options, weights=[POPULARITY[s["service_id"]] for s in options])[0]
                    n = math.ceil(service["duration_minutes"] / 60)
                    span = set(hours[i:i + n])
                    candidates = [
                        t for t in staff
                        if CATEGORY_CODE[service["service_id"]] in t["skills"]
                        and t["hired_on"] <= day
                        and (t["left_on"] is None or day <= t["left_on"])
                        and not (tech_busy[(t["technician_id"], day)] & span)
                    ]
                    if not candidates:
                        slots.append(empty_slot(bid, bay, start, idle))
                        i += 1
                        continue
                    tech = rng.choice(candidates)
                    tech_busy[(tech["technician_id"], day)] |= span

                    row = price_on(bid, service["service_id"], vc, booked_at.date())
                    quoted = round(row["list_price"] * (1 - (row["discount_pct"] or 0) / 100), 2)
                    end = start + timedelta(hours=n)
                    if start > AS_OF:
                        status = "cancelled" if rng.random() < 0.05 else "booked"
                    elif end > AS_OF:
                        status = "in_progress"
                    else:
                        r = rng.random()
                        status = "completed" if r < 0.86 else ("cancelled" if r < 0.94 else "no_show")
                    rating = None
                    if status == "completed" and rng.random() < 0.6:
                        rating = rng.choices([1, 2, 3, 4, 5], weights=[3, 5, 12, 35, 45])[0]

                    booking_seq += 1
                    for k in range(n):
                        slot = empty_slot(bid, bay, start + timedelta(hours=k), status)
                        slot.update({
                            "booking_id": booking_seq, "technician_id": tech["technician_id"],
                            "customer_id": customer["customer_id"], "service_id": service["service_id"],
                            "vehicle_class": vc, "booked_at": booked_at.isoformat(),
                            "price_quoted": quoted, "rating": rating,
                        })
                        slots.append(slot)
                    i += n
            day += timedelta(days=1)

    slots.sort(key=lambda s: (s["start_at"], s["branch_id"], s["bay"]))
    booking_ids = {}
    for slot_id, slot in enumerate(slots, start=1):
        if slot["booking_id"] is not None:
            slot["booking_id"] = booking_ids.setdefault(slot["booking_id"], f"BK-{len(booking_ids) + 1:06d}")
        slots[slot_id - 1] = {"slot_id": slot_id, **slot}

    generated = {"seed": SEED, "as_of": AS_OF.isoformat(), "currency": "USD"}
    write_json(DATA_DIR / "prices.json", {
        "generated": generated,
        "notes": [
            "effective_to is inclusive; null means the price is current.",
            "A missing (branch_id, service_id, vehicle_class) combination means that service is not offered there.",
            "list_price is before discount; discount_pct is null when there is no promotion.",
            "Boston (branch 7) closed on 2025-12-31, so it has price history but no slots.",
        ],
        "branches": BRANCHES,
        "categories": CATEGORIES,
        "vehicle_classes": VEHICLE_CLASSES,
        "services": SERVICES,
        "prices": prices,
    })
    write_json(DATA_DIR / "slots.json", {
        "generated": generated,
        "notes": [
            "Each slot is one 60-minute period in one bay. start_at/end_at are branch-local times; timezones are in prices.json branches[].",
            "Bookings longer than 60 minutes span consecutive slots sharing a booking_id. Booking-level fields (customer_id, service_id, price_quoted, rating) repeat on every slot of the booking, so group by booking_id before summing money.",
            "price_quoted = list_price * (1 - discount_pct/100) from the prices row effective on the booked_at date, not the slot date.",
            "status: available (future, free), unused (past, never booked), blocked (see block_reason), booked (future), in_progress, completed, cancelled, no_show.",
            "Slots before as_of are history; slots after it are the forward booking book.",
        ],
        "technicians": [
            {**t, "skills": sorted(t["skills"]), "hired_on": t["hired_on"].isoformat(),
             "left_on": t["left_on"].isoformat() if t["left_on"] else None}
            for t in technicians
        ],
        "customers": [{k: v for k, v in c.items() if not k.startswith("_")} for c in customers],
        "slots": slots,
    })
    print(f"prices: {len(prices)} rows | technicians: {len(technicians)} | customers: {len(customers)} | slots: {len(slots)} | bookings: {len(booking_ids)}")


def write_json(path: Path, doc: dict) -> None:
    parts = []
    for key, value in doc.items():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            rows = ",\n".join(f"    {json.dumps(row)}" for row in value)
            parts.append(f"  {json.dumps(key)}: [\n{rows}\n  ]")
        else:
            parts.append(f"  {json.dumps(key)}: {json.dumps(value)}")
    path.write_text("{\n" + ",\n".join(parts) + "\n}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
