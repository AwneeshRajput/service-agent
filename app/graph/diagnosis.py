from app.graph import tools
from app.graph.state import GraphState, reply
from app.llm import acomplete_structured
from app.schemas.agents import DiagnosisResult

MIN_SCORE = 0.55

NOT_SURE = (
    "I'm not sure about that from our service manuals. "
    "Please bring the car in so a technician can inspect it."
)

DIAGNOSIS_SYSTEM = """You are a service advisor at a car service centre.
Answer the customer's problem using ONLY the manual excerpts provided. Do not use outside knowledge.
If the excerpts do not clearly cover the problem, set urgency to "unsure" and tell the customer to
bring the car in for inspection.
- answer: 2 to 4 plain sentences: the likely cause and what to do next. Never mention prices.
- urgency: safe_to_drive, book_soon, do_not_drive, or unsure. Follow the urgency the manual gives.
- recommended_service_codes: service codes taken from the excerpts, or an empty list."""

URGENCY_NOTE = {
    "do_not_drive": "Safety warning: please do not drive the car until it has been inspected.",
    "book_soon": "I'd suggest booking an inspection soon.",
}


def format_recalls(car: dict, result: dict) -> str:
    name = f"{car['year']} {car['make']} {car['model']}".upper()
    if result["error"]:
        return f"I couldn't check recalls for your {name} right now ({result['error']}). Please try again later."
    if result["total"] == 0:
        return f"NHTSA lists no recalls for {name} vehicles."

    shown = len(result["recalls"])
    header = f"NHTSA lists {result['total']} recall(s) issued for {name} vehicles"
    header += f" (showing {shown}):" if result["total"] > shown else ":"
    lines = [header]
    for recall in result["recalls"]:
        park = " Do not drive until repaired." if recall["park_it"] else ""
        lines.append(f"- {recall['campaign_number']} ({recall['component']}): {recall['consequence']}{park}")
    lines.append("Recalls apply to the model, not your exact car. Enter your VIN at nhtsa.gov/recalls to see if yours is unrepaired.")
    return "\n".join(lines)


async def diagnosis_node(state: GraphState) -> dict:
    car = state.get("car") or {}
    car_known = all(car.get(key) for key in ("make", "model", "year"))
    is_recall_question = state["intent"] == "recall"

    if is_recall_question and not car_known:
        return reply("Which make, model and year is your car? I'll check it for recalls.")

    parts: list[str] = []
    update: dict = {}

    if not is_recall_question:
        question = state["messages"][-1]["content"]
        chunks = await tools.search_manuals.ainvoke({"question": question, "k": 3})

        if not chunks or chunks[0]["score"] < MIN_SCORE:
            parts.append(NOT_SURE)
        else:
            context = "\n\n".join(f"[{c['doc_id']} / {c['heading']}]\n{c['content']}" for c in chunks)
            user = f"Customer says: {question}\n\nManual excerpts:\n{context}"
            draft = await acomplete_structured(DIAGNOSIS_SYSTEM, user, DiagnosisResult)

            allowed = {code for c in chunks for code in c["service_codes"]}
            codes = [code for code in draft.recommended_service_codes if code in allowed]
            update["diagnosis"] = {
                "answer": draft.answer,
                "urgency": draft.urgency,
                "recommended_service_codes": codes,
                "sources": sorted({c["doc_id"] for c in chunks}),
            }
            parts.append(draft.answer)
            if draft.urgency in URGENCY_NOTE:
                parts.append(URGENCY_NOTE[draft.urgency])

    if car_known:
        recalls = await tools.check_recalls.ainvoke(
            {"make": car["make"], "model": car["model"], "year": car["year"]}
        )
        parts.append(format_recalls(car, recalls))
    elif not is_recall_question:
        parts.append("If you tell me your car's make, model and year, I can also check it for safety recalls.")

    return reply("\n\n".join(parts), **update)
