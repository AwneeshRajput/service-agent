import json
import logging
import time
from collections.abc import AsyncIterator

import openai
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from langgraph.errors import GraphRecursionError
from langgraph.types import Command

from app.config import get_settings
from app.graph.build import graph
from app.llm import LLMOutputError
from app.schemas.chat import ApproveRequest, ChatRequest, ChatResponse, Step

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["chat"])


def describe(node: str, update: dict) -> str:
    if node == "supervisor":
        car = update.get("car") or {}
        text = f"intent = {update['intent']}"
        if car:
            text += f", car = {car.get('year', '?')} {car.get('make', '?')} {car.get('model', '?')}"
        return text
    if node == "diagnosis":
        found = update.get("diagnosis")
        if found:
            return f"urgency = {found['urgency']}, manuals used = {', '.join(found['sources'])}"
        return "no manual diagnosis (recall-only question, or not sure)"
    if node == "estimate":
        estimate = update.get("estimate")
        return f"{estimate['service_code']} priced at ${estimate['price']:.2f}" if estimate else "no estimate produced"
    if node == "booking_propose":
        proposal = update.get("pending_booking")
        return f"proposed slot {proposal['slot_id']} at {proposal['start_at']}" if proposal else "no slot proposed"
    if node == "booking_confirm":
        return update["final_answer"]
    if node == "clarify":
        return "asked one clarifying question"
    if node == "off_topic":
        return "politely declined an off-topic request"
    return "done"


def llm_name() -> str:
    settings = get_settings()
    model = {
        "openai": settings.openai_model,
        "ollama": settings.ollama_model,
        "anthropic": settings.anthropic_model,
    }[settings.llm_provider]
    return f"{settings.llm_provider} {model}"


def node_info(node: str, update: dict) -> tuple[str, str]:
    llm = llm_name()
    if node == "supervisor":
        return "Supervisor agent", f"LLM call ({llm}): classifies the intent and picks the next agent"
    if node == "diagnosis":
        if update.get("diagnosis"):
            return "Diagnosis agent", f"LLM call ({llm}): writes the answer using only the retrieved manual text"
        return "Diagnosis agent", "no LLM call: the recall list is formatted by code from NHTSA data"
    if node == "estimate":
        return "Estimate agent", f"LLM call ({llm}) picks the service code; the price itself comes from the database"
    if node == "booking_propose":
        return "Booking agent (propose)", f"LLM call ({llm}) reads the service and day; code then finds a free slot"
    if node == "booking_confirm":
        return "Booking agent (confirm)", "runs only after the customer approved; then writes the booking to Postgres"
    if node == "clarify":
        return "Clarify agent", "no extra LLM call: asks the question the supervisor already wrote"
    if node == "off_topic":
        return "Off-topic agent", "no LLM call: fixed polite refusal"
    return node, ""


async def get_pending_approval(config: dict):
    snapshot = await graph.aget_state(config)
    return next((i for task in snapshot.tasks for i in task.interrupts), None)


async def iter_graph(graph_input, config: dict) -> AsyncIterator[Step]:
    try:
        async for mode, chunk in graph.astream(graph_input, config, stream_mode=["updates", "custom"]):
            if mode == "custom":
                yield Step(
                    kind="tool",
                    name=chunk["tool"],
                    detail=chunk["detail"],
                    label=f"Tool: {chunk['tool']}",
                    uses=chunk["uses"],
                )
                continue
            for node, update in chunk.items():
                if node == "__interrupt__":
                    yield Step(
                        kind="node",
                        name="approval",
                        detail="paused: waiting for the customer to approve",
                        label="Human approval",
                        uses="LangGraph interrupt(): state saved by the checkpointer, resumes on POST /v1/chat/approve",
                    )
                else:
                    label, uses = node_info(node, update)
                    yield Step(kind="node", name=node, detail=describe(node, update), label=label, uses=uses)
    except LLMOutputError:
        logger.exception("LLM returned invalid output after retries")
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "The assistant could not produce a valid answer. Please rephrase and try again.",
        )
    except openai.APIError:
        logger.exception("LLM provider call failed")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The AI service is unavailable right now. Please try again shortly.",
        )
    except GraphRecursionError:
        logger.exception("graph hit the recursion limit")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "The request took too many steps and was stopped.",
        )


async def run_graph(graph_input, config: dict) -> tuple[list[Step], int]:
    started = time.perf_counter()
    steps = [step async for step in iter_graph(graph_input, config)]
    return steps, int((time.perf_counter() - started) * 1000)


async def build_response(session_id: str, config: dict, steps: list[Step], elapsed_ms: int) -> ChatResponse:
    pending = await get_pending_approval(config)
    if pending:
        return ChatResponse(
            session_id=session_id,
            status="approval_required",
            answer=pending.value["message"],
            intent="booking",
            pending_booking=pending.value["proposal"],
            steps=steps,
            elapsed_ms=elapsed_ms,
        )
    values = (await graph.aget_state(config)).values
    return ChatResponse(
        session_id=session_id,
        status="answered",
        answer=values["final_answer"],
        intent=values.get("intent"),
        steps=steps,
        elapsed_ms=elapsed_ms,
    )


def graph_input_for(request: ChatRequest) -> dict:
    return {
        "messages": [{"role": "user", "content": request.message}],
        "customer_id": request.customer_id,
    }


def ndjson(payload: dict) -> str:
    return json.dumps(payload) + "\n"


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    config = {"configurable": {"thread_id": request.session_id}}

    if await get_pending_approval(config):
        raise HTTPException(status.HTTP_409_CONFLICT, "a booking is waiting for approval: call /v1/chat/approve first")

    steps, elapsed_ms = await run_graph(graph_input_for(request), config)
    return await build_response(request.session_id, config, steps, elapsed_ms)


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    config = {"configurable": {"thread_id": request.session_id}}

    if await get_pending_approval(config):
        raise HTTPException(status.HTTP_409_CONFLICT, "a booking is waiting for approval: call /v1/chat/approve first")

    async def events() -> AsyncIterator[str]:
        steps: list[Step] = []
        started = time.perf_counter()
        try:
            async for step in iter_graph(graph_input_for(request), config):
                steps.append(step)
                yield ndjson({"type": "step", "step": step.model_dump()})
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            response = await build_response(request.session_id, config, steps, elapsed_ms)
            yield ndjson({"type": "result", "response": response.model_dump(mode="json")})
        except HTTPException as error:
            yield ndjson({"type": "error", "status": error.status_code, "detail": error.detail})

    return StreamingResponse(events(), media_type="application/x-ndjson")


@router.post("/chat/approve", response_model=ChatResponse)
async def approve(request: ApproveRequest) -> ChatResponse:
    config = {"configurable": {"thread_id": request.session_id}}

    if not await get_pending_approval(config):
        raise HTTPException(status.HTTP_409_CONFLICT, "nothing is waiting for approval in this session")

    steps, elapsed_ms = await run_graph(Command(resume={"approved": request.approved}), config)
    return await build_response(request.session_id, config, steps, elapsed_ms)
