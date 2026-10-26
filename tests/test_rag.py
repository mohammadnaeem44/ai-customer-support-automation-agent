
from app.rag import answer_question


def test_rag_returns_answer_and_sources():
    result = answer_question(
        "My order is late. What should I do?"
    )

    assert result["answer"]
    assert isinstance(result["sources"], list)
    assert len(result["sources"]) > 0


def test_unsupported_question_requires_review():
    result = answer_question(
        "Can you tell me the current weather on Mars?"
    )

    assert result["requires_human_review"] is True
