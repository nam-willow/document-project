import logging


def get_logger(name: str) -> logging.Logger:
    """
    공통 로거 생성.
    실무에서는 dictConfig 또는 structlog로 확장 가능.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        stream_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger