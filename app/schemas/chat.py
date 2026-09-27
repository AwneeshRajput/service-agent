from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.agents import BookingProposal


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=1000)
    customer_id: int = Field(default=1, ge=1)


class ApproveRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    approved: bool


class Step(BaseModel):
    kind: Literal["node", "tool"]
    name: str
    detail: str
    label: str = ""
    uses: str = ""


class ChatResponse(BaseModel):
    session_id: str
    status: Literal["answered", "approval_required"]
    answer: str
    intent: str | None = None
    pending_booking: BookingProposal | None = None
    steps: list[Step] = []
    elapsed_ms: int = 0
