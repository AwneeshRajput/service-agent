from datetime import date
from functools import lru_cache

from langchain_core.tools import tool
from langgraph.config import get_stream_writer
from sqlalchemy import text

from app.config import get_settings
from app.db import SessionLocal
from app.rag.retriever import search
from app.tools.pricing import get_price as _get_price
from app.tools.recalls import NHTSA_URL
from app.tools.recalls import check_recalls as _check_recalls
from app.tools.slots import book_slot as _book_slot
from app.tools.slots import get_free_slots


def emit(tool_name: str, detail: str, uses: str) -> None:
    try:
        get_stream_writer()({"tool": tool_name, "detail": detail, "uses": uses})
    except RuntimeError:
        pass


def embedding_name() -> str:
    settings = get_settings()
    if settings.embedding_provider == "ollama":
        return f"ollama {settings.ollama_embedding_model}"
    return f"openai {settings.openai_embedding_model}"


@tool
def search_manuals(question: str, k: int = 3) -> list[dict]:
    """Search the service manuals for passages about a car problem. Each result has a similarity score."""
    with SessionLocal() as db:
        chunks = search(db, question, k)
    emit(
        "search_manuals",
        ", ".join(f"{c['doc_id']} {c['score']:.2f}" for c in chunks) or "no matches",
        f"pgvector similarity search on table manual_chunks; the question is embedded with {embedding_name()}",
    )
    return chunks


@tool
async def check_recalls(make: str, model: str, year: int) -> dict:
    """Check NHTSA for safety recalls issued for a vehicle make, model and model year."""
    result = await _check_recalls(make, model, year)
    emit(
        "check_recalls",
        f"{year} {make} {model}: " + (result["error"] or f"{result['total']} recall(s)"),
        f"external NHTSA API: GET {NHTSA_URL}",
    )
    return result


@tool
def get_price(service_code: str, vehicle_class: str | None = None, branch_id: int | None = None) -> list[dict]:
    """Get the current price of a service by its code, for one vehicle class and branch."""
    with SessionLocal() as db:
        rows = _get_price(db, service_code, vehicle_class, branch_id)
    emit(
        "get_price",
        ", ".join(f"{r['service_code']} {r['branch_name']} ${r['price']}" for r in rows) or "no price found",
        "Postgres table prices (same function as GET /v1/prices, called in-process)",
    )
    return rows


@tool
def check_slots(day: date, branch_id: int | None = None) -> list[dict]:
    """List the free booking slots on one day, optionally at one branch."""
    with SessionLocal() as db:
        slots = get_free_slots(db, day, branch_id)
    emit(
        "check_slots",
        f"{len(slots)} free slot(s) on {day}" + (f" at branch {branch_id}" if branch_id else ""),
        "Postgres table slots (same function as GET /v1/slots/free, called in-process)",
    )
    return slots


@tool
def book_slot(slot_id: int, customer_id: int, service_id: int) -> dict:
    """Book a slot for a customer and service. Only call this after the customer has approved."""
    with SessionLocal() as db:
        booking = _book_slot(db, slot_id, customer_id, service_id)
    emit(
        "book_slot",
        f"booked {booking['booking_id']} (slot {slot_id})",
        "Postgres write to table slots (same function as POST /v1/bookings, called in-process)",
    )
    return booking


@lru_cache
def list_services() -> list[dict]:
    with SessionLocal() as db:
        rows = db.execute(
            text("SELECT service_id, code, name, duration_minutes FROM services ORDER BY code")
        ).mappings().all()
    return [dict(row) for row in rows]


def get_service(code: str) -> dict | None:
    return next((s for s in list_services() if s["code"] == code.strip().upper()), None)


def get_customer(customer_id: int) -> dict | None:
    with SessionLocal() as db:
        row = db.execute(
            text("""
                SELECT c.customer_id, c.vehicle_class, c.home_branch_id AS branch_id, b.name AS branch_name
                FROM customers c JOIN branches b ON b.branch_id = c.home_branch_id
                WHERE c.customer_id = :id
            """),
            {"id": customer_id},
        ).mappings().first()
    return dict(row) if row else None
