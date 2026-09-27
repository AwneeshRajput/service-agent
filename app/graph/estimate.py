from app.graph import tools
from app.graph.state import GraphState, reply
from app.llm import acomplete_structured
from app.schemas.agents import EstimateResult, ServicePick

ESTIMATE_SYSTEM = """You match a customer's request to exactly one service from the catalogue below.
Use the conversation for context. If a diagnosis already recommended service codes, treat them as a
strong hint. If it is not clear which single service the customer means, return null.
Catalogue (code: name):
{catalogue}"""


def build_prompt(state: GraphState) -> tuple[str, str]:
    catalogue = "\n".join(f"{s['code']}: {s['name']}" for s in tools.list_services())
    history = "\n".join(f"{m['role']}: {m['content']}" for m in state["messages"][-6:])
    hint = (state.get("diagnosis") or {}).get("recommended_service_codes") or "none"
    return ESTIMATE_SYSTEM.format(catalogue=catalogue), f"Diagnosis hint: {hint}\n\nConversation:\n{history}"


async def estimate_node(state: GraphState) -> dict:
    customer = tools.get_customer(state.get("customer_id", 1))
    if customer is None:
        return reply("I can't find your customer record, so I can't price this yet.")

    system, user = build_prompt(state)
    pick = await acomplete_structured(system, user, ServicePick)
    service = tools.get_service(pick.service_code) if pick.service_code else None
    if service is None:
        return reply("Which service would you like a price for? For example a brake pad replacement or an oil change.")

    rows = await tools.get_price.ainvoke({
        "service_code": service["code"],
        "vehicle_class": customer["vehicle_class"],
        "branch_id": customer["branch_id"],
    })
    if not rows:
        return reply(
            f"We don't offer {service['name']} for your {customer['vehicle_class']} at "
            f"{customer['branch_name']}. I can't give a price for it."
        )

    row = rows[0]
    estimate = EstimateResult(
        service_code=row["service_code"],
        service_name=row["service_name"],
        vehicle_class=row["vehicle_class"],
        branch_name=row["branch_name"],
        duration_minutes=row["duration_minutes"],
        list_price=row["list_price"],
        discount_pct=row["discount_pct"],
        price=row["price"],
    )

    text = f"{estimate.service_name} ({estimate.service_code}) for your {estimate.vehicle_class} at {estimate.branch_name}: ${estimate.price:.2f}"
    if estimate.discount_pct:
        text += f" after a {estimate.discount_pct}% discount (list price ${estimate.list_price:.2f})"
    text += f". It takes about {estimate.duration_minutes} minutes. This is our standard price; the final quote is confirmed after inspection."
    return reply(text, estimate=estimate.model_dump(mode="json"))
