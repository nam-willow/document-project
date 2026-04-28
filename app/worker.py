from celery import Celery
from app.core.config import settings

"""
    FastAPI 서버는 요청을 받고 응답하는 역할인데, OCR처럼 시간이 오래 걸리는 작업을 서버가 직접 처리하면 그 동안 다른 요청을 못 받아요.
                                                                                                                                                                                                                                                                             
    worker.py 없을 때:
        요청 → FastAPI → OCR 처리(10초) → 응답                                                                                                                                                                                                                                   
        (그 10초 동안 다른 요청 대기)
                                                                                                                                                                                                                                                                             
    worker.py 있을 때:
        요청 → FastAPI → "작업 맡겼어요" 즉시 응답                                                                                                                                                                                                                               
                ↓                                                                                                                                                                                                                                                            
        Celery 워커가 백그라운드에서 OCR 처리                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                             
        worker.py는 이 Celery 워커의 설정(어디서 작업을 받을지 = Redis, 결과를 어디에 저장할지 = Redis)을 정의하는 파일이에요.     
"""

celery_app = Celery(
    "document_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.document_task"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    task_track_started=True,
)
