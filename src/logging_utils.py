from __future__ import annotations

import logging
from pathlib import Path


LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def build_logger(name: str = "daily-summarize") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    Path("logs").mkdir(parents=True, exist_ok=True)

    fh = logging.FileHandler("logs/app.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter(LOG_FORMAT))

    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter(LOG_FORMAT))

    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger
