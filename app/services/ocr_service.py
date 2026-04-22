from app.core.logging import get_logger
from app.ml.deep_text_recognition_benchmark.str_predictor import STRPredictor, STRResult
from typing import List, Dict, Any

logger = get_logger(__name__)


class OCRService:
    """
    실제 OCR/ML Skill 연결 전 stub 서비스.
    나중에 LayoutLMv3, PaddleOCR, 외부 ML Skill API 등으로 교체 가능.
    """

    def run_ocr(self, predictor: STRPredictor, file_paths: List[str]) -> List[Dict[str, Any]]:
        logger.info("OCR started | file_path=%s", file_paths)
        results = []
        for path in file_paths:
            try:
                result: STRResult = predictor.predict(path)  # 파일 경로 입력
                
                logger.info(f"result.text: {result.text}")
                results.append({
                "path": path,
                "text": result.text,
                "confidence": result.confidence,
                "elapsed_ms": result.elapsed_ms,
                })
                print(f"★★ results: {results}")
            except FileNotFoundError:
                logger.warning(f"이미지 없음: {path}")
                results.append({"path": path, "text": "", "confidence": 0.0, "error": "file not found"})

            except Exception as e:
                logger.error(f"OCR 실패: {path} | {e}")
                results.append({"path": path, "text": "", "confidence": 0.0, "error": str(e)})
            print("ocr 종료")
        return results
