
from uuid import uuid4

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200


def test_create_ticket():
    response = client.post(
        "/tickets",
        json={
            "customer_id": f"CUST-TEST-{uuid4().hex[:8]}",
            "message": "Where is my order?",
        },
    )

    assert response.status_code in (200, 201), response.text

    data = response.json()
    assert "id" in data
    assert data["message"] == "Where is my order?"
    assert data["classification_status"] in ("completed", "failed")


def test_list_tickets():
    response = client.get("/tickets")

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_get_nonexistent_ticket():
    response = client.get("/tickets/999999999")

    assert response.status_code == 404
