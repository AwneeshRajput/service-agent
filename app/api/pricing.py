from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.pricing import PriceQuote
from app.tools.pricing import get_price
from app.tools.slots import NotFoundError

router = APIRouter(prefix="/v1", tags=["pricing"])


@router.get("/prices", response_model=list[PriceQuote])
def list_prices(
    db: Annotated[Session, Depends(get_db)],
    service_code: str,
    vehicle_class: str | None = None,
    branch_id: int | None = None,
    on_date: Annotated[date | None, Query(alias="date")] = None,
) -> list[dict]:
    try:
        return get_price(db, service_code, vehicle_class, branch_id, on_date)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))