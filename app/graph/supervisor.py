from app.graph.state import GraphState, reply
from app.llm import acomplete_structured
from app.schemas.agents import IntentResult

SUPERVISOR_SYSTEM = """You route messages for a car service centre's front desk.
Pick exactly one intent for the customer's LATEST message, using the conversation for context:
- diagnosis: describes a symptom, noise, smell, warning light or other problem with their car
- recall: asks about safety recalls
- estimate: asks the price or cost of a service or repair (for example "how much?")
- booking: wants to book, schedule or reserve an appointment
- clarify: about their car but too vague to act on
- off_topic: nothing to do with car servicing (poems, general knowledge, chit-chat)
Also extract the car's make, model and year if the customer has stated them, in this or an
earlier message. Leave them null otherwise. Do not guess.
If the intent is clarify, write ONE short question in clarifying_question. Otherwise leave it null."""

ROUTES = {
    "diagnosis": "diagnosis",
    "recall": "diagnosis",
    "estimate": "estimate",
    "booking": "booking_propose",
    "clarify": "clarify",
    "off_topic": "off_topic",
}


async def supervisor_node(state: GraphState) -> dict:
    car = state.get("car") or {}
    history = "\n".join(f"{m['role']}: {m['content']}" for m in state["messages"][-6:])
    user = f"Known car so far: {car or 'unknown'}\n\nConversation:\n{history}"

    result = await acomplete_structured(SUPERVISOR_SYSTEM, user, IntentResult)

    found = {"make": result.make, "model": result.model, "year": result.year}
    car = {**car, **{key: value for key, value in found.items() if value}}
    return {"intent": result.intent, "car": car, "clarifying_question": result.clarifying_question or ""}


def route_by_intent(state: GraphState) -> str:
    return ROUTES[state["intent"]]


async def clarify_node(state: GraphState) -> dict:
    question = state.get("clarifying_question") or "Could you tell me a bit more about what's happening with your car?"
    return reply(question)


async def off_topic_node(state: GraphState) -> dict:
    return reply(
        "Sorry, I can only help with car servicing: diagnosing problems, checking recalls, "
        "pricing and booking appointments. Is there something about your car I can help with?"
    )
