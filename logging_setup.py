"""Central logging config — writes pipeline events to a rotating file log.

Console output stays on rich.Console (human-facing); this captures the same
run to disk so a failed unattended 7am run is diagnosable after the fact.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("logs")


def setup_logging(name: str = "ai_digest") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured (e.g. re-imported)

    LOG_DIR.mkdir(exist_ok=True)
    handler = RotatingFileHandler(
        LOG_DIR / "digest.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
