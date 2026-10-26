
from app.tools import lookup_order


def test_valid_order_lookup():
    result = lookup_order("ORD-1001", "CUST-1001")

    assert result["found"] is True


def test_order_lookup_rejects_wrong_customer():
    result = lookup_order("ORD-1001", "CUST-9999")

    assert result["found"] is False
    assert "not found" in result["message"].lower()
