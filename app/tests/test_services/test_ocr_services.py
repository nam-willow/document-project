import pytest
from app.services.ocr_service import OCRService

"""
예시)
    반환 타입이 dict(내가원하는 타입 인가
    raw_text가 file_type 기반으로 생성되는가
    blocks 개수
    block 구조 (text, confidence)
    confidence 값 범위
"""
# python -m pytest app/tests/test_services/test_ocr_services.py -v

def test_ocr_service_retruns_espected_structure():
    """
    OCRService.run_ocr이 예상된 dict 구조를 반환하는지 검증
    """
    ocr = OCRService()

    result = ocr.run_ocr(file_path="dummy_path", file_type="image")
    
    # 1. 반환타입 검증
    assert isinstance(result, dict)

    # 2. 필수 키 검증
    assert "raw_text" in result
    assert "blocks" in result

    # 3. raw_text 내용 검증 (file_type 기반)
    assert result["raw_text"] == "stub ocr result from image"

    # 4. blocks 구조 검증(문서를 직접 넣으면 개수와 내용 확인을 수정해야함)
    assert isinstance(result["blocks"], list)
    # assert len(result["blocks"]) == 2

    for block in result["blocks"]:
        assert "text" in block
        assert "confidence" in block
        assert isinstance(block["text"], str)
        assert isinstance(block["confidence"], float)
        assert 0.0 <= block["confidence"] <= 1


def test_ocr_service_file_type_affects_output():
    """
    file_type에 따라 raw_text가 달라지는지 검증
    """
    ocr = OCRService()

    result_image = ocr.run_ocr("dummy.png", "image")
    result_pdf = ocr.run_ocr("dummy.pdf", "pdf")

    assert result_image["raw_text"] == "stub ocr result from image"
    assert result_pdf["raw_text"] == "stub ocr result from pdf"


def test_ocr_service_blocks_count():
    """
    blocks 개수 검증
    """
    ocr = OCRService()

    result = ocr.run_ocr("dummy.png", "image")

    assert len(result["blocks"]) == 2


def test_ocr_service_invalid_file_type_still_returns_stub():
    """
    현재 stub 기준: 잘못된 file_type도 그대로 처리됨
    (추후 정책 바뀌면 이 테스트 수정해야 함)
    """
    ocr = OCRService()

    result = ocr.run_ocr("dummy.xyz", "unknown")

    assert result["raw_text"] == "stub ocr result from unknown"
