from datetime import date
from typing import Literal

from pydantic import BaseModel


class IntentResult(BaseModel):
    intent: Literal["diagnosis", "recall", "estimate", "booking", "clarify", "off_topic"]
    make: str | None = None
    model: str | None = None
    year: int | None = None
    clarifying_question: str | None = None


class DiagnosisResult(BaseModel):
    answer: str
    urgency: Literal["safe_to_drive", "book_soon", "do_not_drive", "unsure"]
    recommended_service_codes: list[str] = []


class ServicePick(BaseModel):
    service_code: str | None = None


class BookingWish(BaseModel):
    service_code: str | None = None
    day: date | None = None


class EstimateResult(BaseModel):
    service_code: str
    service_name: str
    vehicle_class: str
    branch_name: str
    duration_minutes: int
    list_price: float
    discount_pct: int | None
    price: float


class BookingProposal(BaseModel):
    slot_id: int
    customer_id: int
    service_id: int
    service_code: str
    service_name: str
    branch_id: int
    branch_name: str
    start_at: str
    price: float
