from app.core.logging import get_logger
from typing import List
from typing import List, Dict, Any

logger = get_logger(__name__)


class ExtractionService:
    """
    OCR 결과에서 필요한 필드 추출.
    어떤 문서를, 
    어떤 필드를, 
    어떤 정확도로 추출할것인가?

    
    """

    def extract_fields(self, ocr_result:  List[Dict[str, Any]]) ->  List[Dict[str, Any]]:
        logger.info("Field extraction started")
        results = []
        # TODO: 실제 필드 추출 모델 결과로 교체
        for result in ocr_result:
            # print(f"Field extraction started | result={ result["text"]}")
            results.append({
                    "document_type": "unknown",
                    "fields": {
                        "name": None,
                        "date": None,
                        "amount": None,
                    },
                    "ocr_preview": result["text"],
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