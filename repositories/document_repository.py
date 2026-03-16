from app.core.logging import get_logger
from app.models.db_models import DocumentRecord

logger = get_logger(__name__)


class DocumentRepository:
    """
    실제 DB 연결 전 임시 repository.
    나중에 SQLAlchemy/SQLModel 등으로 교체.
    """

    def save(self, record: DocumentRecord) -> str:
        logger.info("Pretend save to DB | filename=%s", record.filename)
        # TODO: 실제 DB insert 로직 구현
        return "DB save skipped (stub repository)"