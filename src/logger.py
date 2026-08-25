import logging
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    LOG_DIR.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(LOG_DIR / "bot.log")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger
