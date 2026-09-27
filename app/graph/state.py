import operator
from typing import Annotated, TypedDict


class GraphState(TypedDict, total=False):
    messages: Annotated[list[dict], operator.add]
    customer_id: int
    car: dict
    intent: str
    clarifying_question: str
    diagnosis: dict | None
    estimate: dict | None
    pending_booking: dict | None
    final_answer: str


def reply(text: str, **extra) -> dict:
    return {
        "final_answer": text,
        "messages": [{"role": "assistant", "content": text}],
        **extra,
    }
