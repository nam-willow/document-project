import logging


def get_logger(name: str) -> logging.Logger:
    """
    공통 로거 생성.
    named 로거에 핸들러를 붙이지 않고 루트 로거에 위임(propagate=True 기본값).
    - Celery worker 컨텍스트: Celery가 루트 로거를 선점하므로 Celery 포맷 그대로 사용.
    - uvicorn 단독 컨텍스트: 루트 핸들러가 없을 때만 Celery와 동일한 포맷으로 추가.
    """
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            fmt="[%(asctime)s : %(levelname)s / %(processName)s] %(message)s"
        ))
        root.addHandler(handler)
        root.setLevel(logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    return logger