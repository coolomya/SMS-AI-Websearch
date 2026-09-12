import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Configures dual-stream logging (CLI + Rotating File) preventing duplication."""
    logger = logging.getLogger("search_assistant")
    logger.setLevel(logging.INFO)
    logger.propagate = False  # Stops logs from bubbling up to root Uvicorn threads

    if not logger.handlers:
        log_format = logging.Formatter('%(asctime)s [%(levelname)s] (%(filename)s:%(lineno)d) - %(message)s')

        # Stream 1: Direct console stdout
        cli_handler = logging.StreamHandler()
        cli_handler.setFormatter(log_format)
        logger.addHandler(cli_handler)

        # Stream 2: Automated rolling file logs to prevent disk exhaustion
        file_handler = RotatingFileHandler(
            "search_assistant.log", 
            maxBytes=5_000_000, 
            backupCount=3, 
            encoding="utf-8"
        )
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)
