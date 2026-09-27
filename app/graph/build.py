from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.booking import after_propose, booking_confirm_node, booking_propose_node
from app.graph.diagnosis import diagnosis_node
from app.graph.estimate import estimate_node
from app.graph.state import GraphState
from app.graph.supervisor import ROUTES, clarify_node, off_topic_node, route_by_intent, supervisor_node

RECURSION_LIMIT = 10


def build_graph():
    builder = StateGraph(GraphState)

    builder.add_node("supervisor", supervisor_node)
    builder.add_node("diagnosis", diagnosis_node)
    builder.add_node("estimate", estimate_node)
    builder.add_node("booking_propose", booking_propose_node)
    builder.add_node("booking_confirm", booking_confirm_node)
    builder.add_node("clarify", clarify_node)
    builder.add_node("off_topic", off_topic_node)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges("supervisor", route_by_intent, sorted(set(ROUTES.values())))
    builder.add_conditional_edges("booking_propose", after_propose, ["booking_confirm", END])
    for node in ("diagnosis", "estimate", "booking_confirm", "clarify", "off_topic"):
        builder.add_edge(node, END)

    graph = builder.compile(checkpointer=MemorySaver())
    return graph.with_config(recursion_limit=RECURSION_LIMIT)


graph = build_graph()
