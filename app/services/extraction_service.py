import json
import re
from typing import Any, Dict, List

import anthropic

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Claude에게 전달하는 지시문 (정적 → 프롬프트 캐싱 대상)
_SYSTEM_PROMPT = """당신은 영수증 OCR 텍스트에서 구조화된 정보를 추출하는 전문가입니다.

## 역할
사용자가 제공하는 OCR 텍스트를 분석하여 영수증의 핵심 필드를 JSON 형식으로 반환합니다.

## 추출 필드
- store_name: 가게/매장 이름
- date: 결제 날짜 (YYYY-MM-DD 형식으로 통일)
- total_amount: 최종 결제 금액 (숫자만, 원화 기호 제외)
- items: 구매 상품 목록 (name/price/qty)

## 응답 규칙
1. 반드시 JSON만 반환하고, 설명 텍스트는 절대 포함하지 마세요.
2. 값을 찾을 수 없으면 null로 표시하세요.
3. confidence는 0.0~1.0 사이 실수로, 텍스트에서 해당 값을 얼마나 확신하는지를 나타냅니다.
4. items가 없으면 빈 배열 []로 반환하세요.

## 응답 형식
{
  "document_type": "receipt",
  "fields": {
    "store_name":   {"value": "가게명 또는 null", "confidence": 0.0},
    "date":         {"value": "YYYY-MM-DD 또는 null", "confidence": 0.0},
    "total_amount": {"value": "숫자만 또는 null", "confidence": 0.0},
    "items": [
      {"name": "상품명", "price": "가격", "qty": "수량"}
    ]
  }
}"""


class ExtractionService:

    def __init__(self):
        self._client = None

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._client

    def extract_fields(self, ocr_result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logger.info("Field extraction started | count=%d", len(ocr_result))
        results = []
        for item in ocr_result:
            raw_text = item.get("text", "").strip()
            if not raw_text:
                results.append({"document_type": "unknown", "fields": {}, "ocr_preview": ""})
                continue
            extracted = self._extract_with_claude(raw_text)
            extracted["ocr_preview"] = raw_text
            results.append(extracted)
        return results

    def _extract_with_claude(self, raw_text: str) -> dict:
        if not settings.ANTHROPIC_API_KEY:
            logger.warning("ANTHROPIC_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
            return {"document_type": "unknown", "fields": {}}

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=[
                    {
                        "type": "text",
                        "text": _SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": f"영수증 OCR 텍스트:\n{raw_text}",
                    }
                ],
            )
            response_text = message.content[0].text
            logger.info(
                "Claude 추출 완료 | input_tokens=%d | output_tokens=%d",
                message.usage.input_tokens,
                message.usage.output_tokens,
            )
            return self._parse_json(response_text)

        except anthropic.AuthenticationError:
            logger.error("ANTHROPIC_API_KEY가 유효하지 않습니다.")
            return {"document_type": "unknown", "fields": {}}
        except Exception as e:
            logger.error("Claude API 호출 실패 | error=%s", str(e), exc_info=True)
            return {"document_type": "unknown", "fields": {}}

    def _parse_json(self, text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            logger.warning("JSON 파싱 실패 | text_preview=%s", text[:100])
            return {"document_type": "unknown", "fields": {}}
