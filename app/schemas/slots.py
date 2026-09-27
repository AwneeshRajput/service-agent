from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class FreeSlot(BaseModel):
    slot_id: int
    branch_id: int
    branch_name: str
    bay: int
    start_at: datetime
    end_at: datetime


class BookingRequest(BaseModel):
    slot_id: int
    customer_id: int
    service_id: int


class Booking(BaseModel):
    booking_id: str
    branch_id: int
    bay: int
    start_at: datetime
    end_at: datetime
    service_id: int
    customer_id: int
    technician_id: int
    price_quoted: Decimal
    status: str
