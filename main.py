
import logging
from app.agent import run_agent
from app.tools import lookup_order
from app.rag import answer_question
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from app.database import decide_ticket_review
from app.database import list_tickets
from app.logging_config import logger

from app.database import (
    save_agent_result,
    list_tickets_for_review,
)

from app.database import (
    create_ticket,
    get_ticket,
    list_tickets,
    update_ticket_classification,
)
from app.database import (
    create_ticket,
    get_ticket,
    list_tickets,
    update_ticket_classification,
    update_classification_status,
)
from app.database import (
    create_ticket,
    get_ticket,
    list_tickets,
    update_ticket_classification,
    update_classification_status,
    update_escalation,
)
from app.ai_classifier import classify_ticket


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Customer Support Automation Agent",
    description="An AI agent for ticket classification and customer support",
    version="0.3.0",
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


@app.post("/agent")
def agent_endpoint(request: AgentRequest):
    # Save the ticket before calling external AI services.
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

@app.get("/tickets/review")
def review_queue(
    limit: int = Query(default=50, ge=1, le=100),
):
    return list_tickets_for_review(limit=limit)


@app.post("/tools/order-lookup")
def order_lookup_endpoint(request: OrderLookupRequest):
    return lookup_order(
        order_id=request.order_id,
        customer_id=request.customer_id,
    )

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

@app.get("/")
def root():
    return {
        "message": "Customer Support Agent API is running",
        "version": "0.3.0",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/tickets/preview")
def preview_ticket(ticket: TicketRequest):
    return {
        "customer_id": ticket.customer_id,
        "message": ticket.message,
        "status": "received",
    }

@app.get("/tickets")
def get_all_tickets():
    tickets = list_tickets()
    return tickets


@app.post("/tickets", status_code=201)
def submit_ticket(ticket: TicketRequest):
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
            raise RuntimeError("Ticket was not found after updating.")

        intent = classification["intent"]
        priority = classification["priority"]

        requires_review = (
            priority == "urgent"
            or intent in {"refund", "cancellation", "account_issue"}
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
            "Classification failed for ticket ID %s",
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

        # Preserve the original ticket if AI classification fails.
        return get_ticket(saved_ticket["id"]) or saved_ticket

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )

    return ticket
