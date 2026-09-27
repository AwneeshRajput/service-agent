from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class PriceQuote(BaseModel):
    service_code: str
    service_name: str
    duration_minutes: int
    branch_id: int
    branch_name: str
    vehicle_class: str
    list_price: Decimal
    discount_pct: int | None
    price: Decimal
    effective_from: date
    effective_to: date | None
