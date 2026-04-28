from pathlib import Path

from app.worker import celery_app
from app.core.logging import get_logger
from app.services.file_service import FileService
from app.ml.easyocr_predictor import EasyOCRPredictor

logger = get_logger(__name__)

# Worker 시작 시 1회 초기화 (모델 로딩 비용이 크기 때문에 모듈 레벨에 배치)
_file_service = FileService()
_predictor = EasyOCRPredictor(lang=["ko", "en"])


@celery_app.task(bind=True, max_retries=3)
def process_document_task(self, file_path: str, file_type: str) -> dict:
    logger.info("Task started | file_path=%s | file_type=%s", file_path, file_type)
    try:
        result = _file_service.process_file(
            predictor=_predictor,
            file_path=Path(file_path),
            file_type=file_type,
            save_to_db=False,
        )
        logger.info("Task completed | file_path=%s", file_path)
        return result
    except Exception as exc:
        logger.error("Task failed | error=%s", str(exc), exc_info=True)
        raise self.retry(exc=exc, countdown=5)
