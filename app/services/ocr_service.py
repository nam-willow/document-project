from app.core.logging import get_logger
from app.ml.str_predictor import STRPredictor, STRResult

logger = get_logger(__name__)


class OCRService:
    """
    실제 OCR/ML Skill 연결 전 stub 서비스.
    나중에 LayoutLMv3, PaddleOCR, 외부 ML Skill API 등으로 교체 가능.
    """

    def run_ocr(self, predictor: STRPredictor, file_paths: list[str]) -> list[str]:
        logger.info("OCR started | file_type=%s | file_path=%s", file_paths)
        results = []
        for path in file_paths:
            try:
                result: STRResult = predictor.predict(path)  # 파일 경로 입력
                results.append({
                "path": path,
                "text": result.text,
                "confidence": result.confidence,
                "elapsed_ms": result.elapsed_ms,
                })

            except FileNotFoundError:
                logger.warning(f"이미지 없음: {path}")
                results.append({"path": path, "text": "", "confidence": 0.0, "error": "file not found"})

            except Exception as e:
                logger.error(f"OCR 실패: {path} | {e}")
                results.append({"path": path, "text": "", "confidence": 0.0, "error": str(e)})

        return results

        # # TODO: 실제 OCR/ML Skill 호출로 교체
        # return {
        #     "raw_text": f"stub ocr result from {file_type}",
        #     "blocks": [
        #         {"text": "sample_text_1", "confidence": 0.98},
        #         {"text": "sample_text_2", "confidence": 0.95},
        #     ],
        # }