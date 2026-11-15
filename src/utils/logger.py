"""Structured logging configuration for ClimaData Perú."""

import logging
import sys
from typing import Optional


def setup_logger(name: str = "climadata", level: Optional[str] = None) -> logging.Logger:
    """Configura y retorna un logger formateado de manera profesional."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)

    log_level = getattr(logging, (level or "INFO").upper(), logging.INFO)
    logger.setLevel(log_level)
    return logger
