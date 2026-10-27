
import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agent import run_agent
from app.ai_classifier import classify_ticket
from app.database import (
    create_ticket,
    decide_ticket_review,
    get_ticket,
    list_tickets,
    list_tickets_for_review,
    save_agent_result,
    update_classification_status,
    update_escalation,
    update_ticket_classification,
)
from app.logging_config import logger
from app.rag import answer_question
from app.tools import lookup_order


logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="AI Customer Support Automation Agent",
    description="An AI agent for ticket classification and customer support",
    version="0.3.0",
)

# Allow the local website chat frontend to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TicketRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=3, max_length=5000)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=3000)


class OrderLookupRequest(BaseModel):
    order_id: str = Field(min_length=1, max_length=50)
    customer_id: str = Field(min_length=1, max_length=100)


class AgentRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=3, max_length=5000)
    order_id: str | None = Field(default=None, max_length=50)


class ReviewRequest(BaseModel):
    decision: str


@app.get("/")
def root():
    return {
        "message": "Customer Support Agent API is running",
        "version": "0.3.0",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/ask")
def ask_support_question(request: AskRequest):
    try:
        return answer_question(request.question)
    except Exception:
        logger.exception("Support question answering failed")
        raise HTTPException(
            status_code=502,
            detail="The support assistant is temporarily unavailable.",
        )


@app.post("/tickets/preview")
def preview_ticket(ticket: TicketRequest):
    return {
        "customer_id": ticket.customer_id,
        "message": ticket.message,
        "status": "received",
    }


@app.post("/tickets", status_code=201)
def submit_ticket(ticket: TicketRequest):
    # Save the original ticket before calling the AI service.
    saved_ticket = create_ticket(
        customer_id=ticket.customer_id,
        message=ticket.message,
    )

    try:
        classification = classify_ticket(ticket.message)

        updated_ticket = update_ticket_classification(
            ticket_id=saved_ticket["id"],
            intent=classification["intent"],
            sentiment=classification["sentiment"],
            priority=classification["priority"],
        )

        if updated_ticket is None:
            raise RuntimeError("Ticket was not found after classification.")

        requires_review = (
            classification["priority"] == "urgent"
            or classification["intent"]
            in {"refund", "cancellation", "account_issue"}
        )

        updated_ticket = update_escalation(
            ticket_id=saved_ticket["id"],
            requires_human_review=requires_review,
        )

        if updated_ticket is None:
            raise RuntimeError("Ticket was not found after escalation update.")

        return updated_ticket

    except Exception:
        logger.exception(
            "Ticket classification failed for ticket ID %s",
            saved_ticket["id"],
        )

        try:
            update_classification_status(
                ticket_id=saved_ticket["id"],
                status="failed",
            )
        except Exception:
            logger.exception(
                "Could not update classification status for ticket ID %s",
                saved_ticket["id"],
            )

        # Preserve the ticket even if AI classification fails.
        return get_ticket(saved_ticket["id"]) or saved_ticket


@app.get("/tickets")
def get_all_tickets():
    return list_tickets()


@app.get("/tickets/review")
def review_queue(
    limit: int = Query(default=50, ge=1, le=100),
):
    return list_tickets_for_review(limit=limit)


@app.get("/tickets/{ticket_id}")
def get_ticket_endpoint(ticket_id: int):
    ticket = get_ticket(ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )

    return ticket


@app.post("/tickets/{ticket_id}/review")
def review_ticket(ticket_id: int, request: ReviewRequest):
    if request.decision not in {"approved", "rejected"}:
        raise HTTPException(
            status_code=422,
            detail="Decision must be approved or rejected.",
        )

    ticket = decide_ticket_review(
        ticket_id=ticket_id,
        decision=request.decision,
    )

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Pending review ticket not found.",
        )

    return ticket


@app.post("/tools/order-lookup")
def order_lookup_endpoint(request: OrderLookupRequest):
    return lookup_order(
        order_id=request.order_id,
        customer_id=request.customer_id,
    )


@app.post("/agent")
def agent_endpoint(request: AgentRequest):
    # Save the ticket before running the agent.
    saved_ticket = create_ticket(
        customer_id=request.customer_id,
        message=request.message,
    )

    try:
        result = run_agent(
            customer_id=request.customer_id,
            message=request.message,
            order_id=request.order_id,
        )

        saved_result = save_agent_result(
            ticket_id=saved_ticket["id"],
            result=result,
        )

        if saved_result is None:
            raise RuntimeError("Could not save agent result.")

        result["ticket"] = saved_result
        return result

    except Exception:
        logger.exception(
            "Agent workflow failed for ticket %s",
            saved_ticket["id"],
        )

        raise HTTPException(
            status_code=502,
            detail={
                "message": "Agent processing failed.",
                "ticket_id": saved_ticket["id"],
                "ticket_preserved": True,
            },
        )
