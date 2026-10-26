
# Simulated order data for development and testing.
# Replace this with a real order-management API in production.

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


def lookup_order(order_id: str, customer_id: str):
    """Return an order only when both identifiers match."""
    order = ORDERS.get(order_id.strip().upper())

    if not order or order["customer_id"] != customer_id:
        return {
            "found": False,
            "message": "Order not found for the supplied customer.",
        }

    return {
        "found": True,
        "order": order,
    }
