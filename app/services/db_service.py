from app.core.logging import get_logger
from app.models.db_models import DocumentRecord
from app.repositories.document_repository import DocumentRepository

logger = get_logger(__name__)


class DBService:
    def __init__(self) -> None:
        self.repository = DocumentRepository()

    def save_document_result(
        self,
        filename: str,
        file_type: str,
        saved_path: str,
        extracted_json: dict,
    ) -> str:
        logger.info("DB save requested | filename=%s", filename)
        print("DB save requested | filename=%s", filename)
        record = DocumentRecord(
            filename=filename,
            file_type=file_type,
            saved_path=saved_path,
            extracted_json=extracted_json,
        )
        return self.repository.save(record)