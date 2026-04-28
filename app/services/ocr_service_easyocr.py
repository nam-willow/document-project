from app.core.logging import get_logger
from app.ml.easyocr_predictor import EasyOCRPredictor, OCRResult
from typing import List, Dict, Any

logger = get_logger(__name__)


class OCRService:

    def run_ocr(
        self,
        predictor: EasyOCRPredictor,
        file_paths: List[str],
    ) -> List[Dict[str, Any]]:

        if not file_paths:
            logger.warning("run_ocr: file_paths 비어 있음")
            return []

        logger.info("OCR 시작 | 총 파일 수=%d", len(file_paths))
        results = []

        for idx, path in enumerate(file_paths, start=1):
            try:
                logger.info("OCR 처리 중 | path = %s", path)
                result: OCRResult = predictor.predict(path)
                results.append({
                    "path": path,
                    "text": result.text,
                    "lines": result.lines,
                    "confidence": result.confidence,
                    "elapsed_ms": result.elapsed_ms,
                })
                logger.info(
                    "OCR 성공 [%d/%d] | confidence=%.4f | text_preview=%s",
                    idx, len(file_paths),
                    result.confidence,
                    result.text[:30],  # 앞 30자만 로그 출력
                )

            except FileNotFoundError:
                logger.warning("이미지 없음 [%d/%d] | path=%s", idx, len(file_paths), path)
                results.append({
                    "path": path, "text": "", "lines": [],
                    "confidence": 0.0, "elapsed_ms": 0.0,
                    "error": "file not found",
                })

            except Exception as e:
                logger.error(
                    "OCR 실패 [%d/%d] | path=%s | error=%s",
                    idx, len(file_paths), path, str(e),
                    exc_info=True,
                )
                results.append({
                    "path": path, "text": "", "lines": [],
                    "confidence": 0.0, "elapsed_ms": 0.0,
                    "error": str(e),
                })

        return results