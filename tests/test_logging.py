
from app.logging_config import logger


def test_logger_is_configured():
    assert logger.name == "support_agent"
    assert logger.level == 20  # logging.INFO
    assert len(logger.handlers) >= 1
