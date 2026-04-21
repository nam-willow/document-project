from app.core.logging import get_logger
from typing import List

logger = get_logger(__name__)


class ExtractionService:
    """
    OCR 결과에서 필요한 필드 추출.
    나중에 학습된 추출 모델 결과를 여기에서 반환하도록 설계.
    """

    def extract_fields(self, ocr_result:  List[str]) ->  List[str]:
        logger.info("Field extraction started")
        results = []
        # TODO: 실제 필드 추출 모델 결과로 교체
        for result in ocr_result:
            print("Field extraction started | result=%s", result)
            results.append({
                    "document_type": "unknown",
                    "fields": {
                        "name": None,
                        "date": None,
                        "amount": None,
                    },
                    "ocr_preview": result.get("text", ""),
                    })
        # return {
        #     "document_type": "unknown",
        #     "fields": {
        #         "name": None,
        #         "date": None,
        #         "amount": None,
        #     },
        #     "ocr_preview": ocr_result.get("raw_text"),
        # }
        return results