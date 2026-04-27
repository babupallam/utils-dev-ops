from __future__ import annotations

import logging


def build_logger(log_level: str) -> logging.Logger:
    """Build configured application logger.

    Args:
        log_level: Logging level name such as INFO or DEBUG.

    Returns:
        Configured logger instance.
    """

    logger = logging.getLogger("yt_subtitle_engine")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    logger.addHandler(handler)
    logger.propagate = False

    return logger