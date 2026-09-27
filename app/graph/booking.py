from datetime import date, datetime, timedelta
from math import ceil

from langgraph.graph import END
from langgraph.types import interrupt

from app.graph import tools
from app.graph.state import GraphState, reply
from app.llm import acomplete_structured
from app.schemas.agents import BookingProposal, BookingWish
from app.tools.slots import BookingError, NotFoundError

BOOKING_SYSTEM = """From the conversation, work out which service the customer wants to book and on which day.
Today is {today} ({weekday}). Turn relative days such as "Saturday" or "tomorrow" into the next
upcoming date, written as YYYY-MM-DD. If the customer says "book it" or similar, use the service
already discussed: {known}. Return null for anything that is not clear.
Service catalogue (code: name):
{catalogue}"""


def find_slot(slots: list[dict], hours_needed: int) -> dict | None:
    free = {(s["bay"], s["start_at"]) for s in slots}
    for slot in slots:
        if all((slot["bay"], slot["start_at"] + timedelta(hours=h)) in free for h in range(hours_needed)):
            return slot
    return None


def when(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%A %d %B at %H:%M")


async def booking_propose_node(state: GraphState) -> dict:
    customer = tools.get_customer(state.get("customer_id", 1))
    if customer is None:
        return reply("I can't find your customer record, so I can't book yet.", pending_booking=None)

    today = date.today()
    known = (state.get("estimate") or {}).get("service_code") or (
        ((state.get("diagnosis") or {}).get("recommended_service_codes") or [None])[0]
    )
    system = BOOKING_SYSTEM.format(
        today=today.isoformat(),
        weekday=today.strftime("%A"),
        known=known or "none",
        catalogue="\n".join(f"{s['code']}: {s['name']}" for s in tools.list_services()),
    )
    history = "\n".join(f"{m['role']}: {m['content']}" for m in state["messages"][-6:])
    wish = await acomplete_structured(system, f"Conversation:\n{history}", BookingWish)

    service = tools.get_service(wish.service_code or known or "")
    if service is None:
        return reply("Which service would you like to book?", pending_booking=None)
    if wish.day is None:
        return reply("Which day would you like to come in?", pending_booking=None)
    if wish.day < today:
        return reply("That date has already passed. Which upcoming day works for you?", pending_booking=None)

    slots = await tools.check_slots.ainvoke({"day": wish.day.isoformat(), "branch_id": customer["branch_id"]})
    slots = [s for s in slots if s["start_at"] > datetime.now()]
    slot = find_slot(slots, ceil(service["duration_minutes"] / 60))
    if slot is None:
        return reply(
            f"There are no free openings for {service['name']} at {customer['branch_name']} on "
            f"{wish.day.strftime('%A %d %B')}. Would another day work?",
            pending_booking=None,
        )

    prices = await tools.get_price.ainvoke({
        "service_code": service["code"],
        "vehicle_class": customer["vehicle_class"],
        "branch_id": customer["branch_id"],
    })
    if not prices:
        return reply(
            f"We don't offer {service['name']} for your vehicle at {customer['branch_name']}.",
            pending_booking=None,
        )

    proposal = BookingProposal(
        slot_id=slot["slot_id"],
        customer_id=customer["customer_id"],
        service_id=service["service_id"],
        service_code=service["code"],
        service_name=service["name"],
        branch_id=customer["branch_id"],
        branch_name=customer["branch_name"],
        start_at=slot["start_at"].isoformat(),
        price=prices[0]["price"],
    )
    return {"pending_booking": proposal.model_dump(mode="json")}


def after_propose(state: GraphState) -> str:
    return "booking_confirm" if state.get("pending_booking") else END


async def booking_confirm_node(state: GraphState) -> dict:
    proposal = state["pending_booking"]

    decision = interrupt({
        "message": (
            f"I can book {proposal['service_name']} at {proposal['branch_name']} on "
            f"{when(proposal['start_at'])} for ${proposal['price']:.2f}. Shall I go ahead?"
        ),
        "proposal": proposal,
    })

    if not decision.get("approved"):
        return reply("No problem, I haven't booked anything. Tell me if you'd like a different time.", pending_booking=None)

    try:
        booking = await tools.book_slot.ainvoke({
            "slot_id": proposal["slot_id"],
            "customer_id": proposal["customer_id"],
            "service_id": proposal["service_id"],
        })
    except (BookingError, NotFoundError) as error:
        return reply(f"Sorry, I couldn't complete the booking: {error}. Would you like to try another time?", pending_booking=None)

    return reply(
        f"Booked! Reference {booking['booking_id']}: {proposal['service_name']} at "
        f"{proposal['branch_name']} on {when(proposal['start_at'])}, ${booking['price_quoted']:.2f}.",
        pending_booking=None,
    )
