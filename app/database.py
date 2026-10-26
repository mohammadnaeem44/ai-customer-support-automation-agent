
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "support.db"

def decide_ticket_review(ticket_id: int, decision: str):
    if decision not in {"approved", "rejected"}:
        raise ValueError("Decision must be approved or rejected.")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE tickets
            SET review_status = ?
            WHERE id = ?
              AND review_status = 'pending'
            """,
            (decision, ticket_id),
        )

        if cursor.rowcount == 0:
            return None

        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()

        return dict(row) if row else None

def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                intent TEXT,
                sentiment TEXT,
                priority TEXT,
                created_at TEXT NOT NULL
            )
        """)


def migrate_database():
    """Add new columns safely without deleting existing tickets."""
    with get_connection() as connection:
        columns = connection.execute(
            "PRAGMA table_info(tickets)"
        ).fetchall()

        column_names = {column["name"] for column in columns}

        if "classification_status" not in column_names:
            connection.execute("""
                ALTER TABLE tickets
                ADD COLUMN classification_status
                TEXT NOT NULL DEFAULT 'pending'
            """)
        if "requires_human_review" not in column_names:
            connection.execute("""
                ALTER TABLE tickets
                ADD COLUMN requires_human_review
                INTEGER NOT NULL DEFAULT 0
            """)

        if "review_status" not in column_names:
            connection.execute("""
                ALTER TABLE tickets
                ADD COLUMN review_status
                TEXT NOT NULL DEFAULT 'not_required'
            """)


def update_escalation(
    ticket_id: int,
    requires_human_review: bool,
):
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE tickets
            SET requires_human_review = ?
            WHERE id = ?
            """,
            (int(requires_human_review), ticket_id),
        )

        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()

        return dict(row) if row else None



def create_ticket(customer_id: str, message: str):
    created_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO tickets (customer_id, message, created_at)
            VALUES (?, ?, ?)
            """,
            (customer_id, message, created_at),
        )

        ticket_id = cursor.lastrowid

        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()

        return dict(row)


def get_ticket(ticket_id: int):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()

        return dict(row) if row else None


def list_tickets(limit: int = 50):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM tickets
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [dict(row) for row in rows]


def update_ticket_classification(
    ticket_id: int,
    intent: str,
    sentiment: str,
    priority: str,
):
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE tickets
            SET intent = ?,
                sentiment = ?,
                priority = ?,
                classification_status = 'completed'
            WHERE id = ?
            """,
            (intent, sentiment, priority, ticket_id),
        )

        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()

        return dict(row) if row else None



def update_classification_status(ticket_id: int, status: str):
    allowed_statuses = {"pending", "completed", "failed"}

    if status not in allowed_statuses:
        raise ValueError("Invalid classification status.")

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE tickets
            SET classification_status = ?
            WHERE id = ?
            """,
            (status, ticket_id),
        )

        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()

        return dict(row) if row else None


def save_agent_result(ticket_id: int, result: dict):
    classification = result["classification"]
    requires_review = result["requires_human_review"]

    review_status = (
        "pending" if requires_review else "not_required"
    )

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE tickets
            SET intent = ?,
                sentiment = ?,
                priority = ?,
                classification_status = 'completed',
                requires_human_review = ?,
                review_status = ?
            WHERE id = ?
            """,
            (
                classification["intent"],
                classification["sentiment"],
                classification["priority"],
                int(requires_review),
                review_status,
                ticket_id,
            ),
        )

        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()

        return dict(row) if row else None


def list_tickets_for_review(limit: int = 50):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM tickets
            WHERE review_status = 'pending'
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [dict(row) for row in rows]


# Initialize and migrate the database when this module is imported.
initialize_database()
migrate_database()
