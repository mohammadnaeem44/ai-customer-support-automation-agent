
# Simulated order data for development and testing.
# Replace this adapter with an authorized order-management API later.

ORDERS = {
    "ORD-1001": {
        "order_id": "ORD-1001",
        "customer_id": "CUST-1001",
        "status": "shipped",
        "estimated_delivery": "2026-10-28",
    },
    "ORD-1002": {
        "order_id": "ORD-1002",
        "customer_id": "CUST-1002",
        "status": "processing",
        "estimated_delivery": "2026-10-30",
    },
    "ORD-1003": {
        "order_id": "ORD-1003",
        "customer_id": "CUST-1003",
        "status": "delayed",
        "estimated_delivery": "2026-10-25",
    },
}


def lookup_order(order_id: str, customer_id: str) -> dict:
    """Return an order only when both identifiers match."""

    if not order_id or not customer_id:
        return {
            "found": False,
            "message": "An order ID and customer ID are required.",
        }

    normalized_order_id = order_id.strip().upper()
    normalized_customer_id = customer_id.strip()

    order = ORDERS.get(normalized_order_id)

    if not order or order["customer_id"] != normalized_customer_id:
        return {
            "found": False,
            "message": "Order not found for the supplied customer.",
        }

    # Return a copy rather than exposing the stored dictionary.
    return {
        "found": True,
        "order": order.copy(),
    }
