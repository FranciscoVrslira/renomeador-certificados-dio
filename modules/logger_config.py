"""Logs UTF-8 no console e em arquivo próprio por execução."""
from datetime import datetime
import logging
import os
from pathlib import Path


def configure_logger(folder: Path, level: str) -> logging.Logger:
    folder.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("dio")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    logger.setLevel(level)
    logger.propagate = False
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    handlers = [logging.StreamHandler(), logging.FileHandler(
        folder / f"execucao_{stamp}_{os.getpid()}.log", encoding="utf-8")]
    for handler in handlers:
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(handler)
    return logger
