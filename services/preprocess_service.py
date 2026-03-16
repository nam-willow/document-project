from app.core.logging import get_logger

logger = get_logger(__name__)


class PreprocessService:
    """
    파일 유형별 전처리 분기.
    실제 이미지/PDF 전처리는 나중에 구현 예정.
    """

    def preprocess_image(self, file_path: str) -> str:
        logger.info("Image preprocessing started: %s", file_path)
        # TODO: 이미지 전처리 로직 구현
        return file_path

    def preprocess_pdf(self, file_path: str) -> str:
        logger.info("PDF preprocessing started: %s", file_path)
        # TODO: PDF 전처리 로직 구현
        return file_path