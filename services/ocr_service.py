from app.core.logging import get_logger

logger = get_logger(__name__)


class OCRService:
    """
    실제 OCR/ML Skill 연결 전 stub 서비스.
    나중에 LayoutLMv3, PaddleOCR, 외부 ML Skill API 등으로 교체 가능.
    """

    def run_ocr(self, file_path: str, file_type: str) -> dict:
        logger.info("OCR started | file_type=%s | file_path=%s", file_type, file_path)

        # TODO: 실제 OCR/ML Skill 호출로 교체
        return {
            "raw_text": f"stub ocr result from {file_type}",
            "blocks": [
                {"text": "sample_text_1", "confidence": 0.98},
                {"text": "sample_text_2", "confidence": 0.95},
            ],
        }