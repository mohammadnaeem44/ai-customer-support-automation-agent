
from app.ai_classifier import classify_ticket
from app.rag import answer_question
from app.tools import lookup_order
from app.logging_config import logger


def run_agent(
    customer_id: str,
    message: str,
    order_id: str | None = None,
):
    logger.info("Agent workflow started")

    try:
        # 1. Classify the customer's message.
        classification = classify_ticket(message)

        intent = classification["intent"]
        priority = classification["priority"]

        # 2. Identify cases requiring human review.
        sensitive_intents = {
            "refund",
            "cancellation",
            "account_issue",
            "payment_issue",
        }

        requires_human_review = (
            priority == "urgent"
            or intent in sensitive_intents
        )

        # 3. Look up order information when an order ID is supplied.
        order_result = None

        if order_id:
            order_result = lookup_order(
                order_id=order_id,
                customer_id=customer_id,
            )

            if not order_result["found"]:
                requires_human_review = True

        # 4. Retrieve a grounded answer from the knowledge base.
        rag_result = answer_question(message)

        if rag_result["requires_human_review"]:
            requires_human_review = True

        # 5. Never automatically approve sensitive requests.
        if intent in {"refund", "cancellation"}:
            answer = (
                "Your request has been received. It requires verification "
                "and human review before any refund or cancellation is approved."
            )
        else:
            answer = rag_result["answer"]

        result = {
            "customer_id": customer_id,
            "message": message,
            "classification": classification,
            "order_lookup": order_result,
            "answer": answer,
            "sources": rag_result["sources"],
            "requires_human_review": requires_human_review,
            "workflow_status": (
                "pending_human_review"
                if requires_human_review
                else "answered"
            ),
        }

        logger.info(
            "Agent workflow completed | intent=%s | status=%s | human_review=%s",
            intent,
            result["workflow_status"],
            result["requires_human_review"],
        )

        return result

    except Exception:
        logger.exception("Agent workflow failed")
        raise
