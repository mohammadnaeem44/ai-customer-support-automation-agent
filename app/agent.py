
from app.ai_classifier import classify_ticket
from app.rag import answer_question
from app.tools import lookup_order
from app.logging_config import logger


SENSITIVE_INTENTS = {
    "refund",
    "cancellation",
    "account_issue",
    "payment_issue",
}

ORDER_KEYWORDS = (
    "order",
    "tracking",
    "track my",
    "delivery",
    "delivered",
    "shipment",
    "shipped",
)


def run_agent(
    customer_id: str,
    message: str,
    order_id: str | None = None,
):
    logger.info("Agent workflow started")

    try:
        classification = classify_ticket(message)

        intent = classification["intent"]
        priority = classification["priority"]
        normalized_message = message.lower()

        requires_review = (
            priority == "urgent"
            or intent in SENSITIVE_INTENTS
        )

        order_related = (
            intent == "order_status"
            or any(
                keyword in normalized_message
                for keyword in ORDER_KEYWORDS
            )
        )

        order_result = None

        # Order actions must use verified order data.
        if order_related and order_id:
            order_result = lookup_order(
                order_id=order_id,
                customer_id=customer_id,
            )

            if not order_result["found"]:
                requires_review = True
                answer = (
                    "I couldn't verify that order using the supplied "
                    "details. Please check the order ID and contact "
                    "support if the problem continues."
                )

            else:
                order = order_result["order"]
                answer = (
                    f"Order {order['order_id']} status: "
                    f"{order['status']}. "
                    f"Estimated delivery: "
                    f"{order['estimated_delivery']}."
                )

        elif order_related:
            answer = (
                "I can help check your order. Please provide your "
                "order ID so I can look it up. For your privacy, "
                "order details will only be returned after the "
                "customer and order details have been verified."
            )

        else:
            rag_result = answer_question(message)

            if rag_result["requires_human_review"]:
                requires_review = True

            answer = rag_result["answer"]

        # Never claim that a cancellation or refund has been completed.
        if intent in {"refund", "cancellation"}:
            requires_review = True

            if order_id and order_result and order_result["found"]:
                answer = (
                    "I've verified the order details. Your "
                    "cancellation or refund request still requires "
                    "human review. No change has been made to your order."
                )
            else:
                answer = (
                    "Your request requires verification and human "
                    "review. Please provide your order ID so support "
                    "can review the correct order. No cancellation "
                    "or refund has been processed."
                )

        sources = (
            rag_result["sources"]
            if not order_related
            else []
        )

        result = {
            "customer_id": customer_id,
            "message": message,
            "classification": classification,
            "order_lookup": order_result,
            "answer": answer,
            "sources": sources,
            "requires_human_review": requires_review,
            "workflow_status": (
                "pending_human_review"
                if requires_review
                else "answered"
            ),
        }

        logger.info(
            "Agent workflow completed | intent=%s | status=%s "
            "| human_review=%s",
            intent,
            result["workflow_status"],
            result["requires_human_review"],
        )

        return result

    except Exception:
        logger.exception("Agent workflow failed")
        raise
