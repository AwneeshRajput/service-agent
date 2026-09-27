from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.slots import Booking, BookingRequest, FreeSlot
from app.tools.slots import BookingError, NotFoundError, book_slot, get_free_slots

router = APIRouter(prefix="/v1", tags=["slots"])

@router.get("/slots/free", response_model=list[FreeSlot])
def list_free_slots(
    db: Annotated[Session, Depends(get_db)],
    day: Annotated[date, Query(alias="date")],
    branch_id: int | None = None,
) -> list[dict]:
    return get_free_slots(db, day, branch_id)


@router.post("/bookings", response_model=Booking, status_code=status.HTTP_201_CREATED)
def create_booking(request: BookingRequest, db: Annotated[Session, Depends(get_db)]) -> dict:
    try:
        return book_slot(db, request.slot_id, request.customer_id, request.service_id)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except BookingError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
