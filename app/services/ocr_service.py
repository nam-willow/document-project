from app.core.logging import get_logger
from app.ml.str_predictor import STRPredictor, STRResult

logger = get_logger(__name__)


class OCRService:
    """
    실제 OCR/ML Skill 연결 전 stub 서비스.
    나중에 LayoutLMv3, PaddleOCR, 외부 ML Skill API 등으로 교체 가능.
    """

    def run_ocr(self, predictor: STRPredictor, file_path: str, file_type: str) -> dict:
        logger.info("OCR started | file_type=%s | file_path=%s", file_type, file_path)

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            result: STRResult = predictor.predict(content)  # bytes 입력
        except Exception as e:
            logger.exception("추론 실패")
            # raise HTTPException(status_code=500, detail=str(e))

        return PredictResponse(
            text=result.text,
            confidence=result.confidence,
            elapsed_ms=result.elapsed_ms,
        )

        # # TODO: 실제 OCR/ML Skill 호출로 교체
        # return {
        #     "raw_text": f"stub ocr result from {file_type}",
        #     "blocks": [
        #         {"text": "sample_text_1", "confidence": 0.98},
        #         {"text": "sample_text_2", "confidence": 0.95},
        #     ],
        # }