import io
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi import HTTPException, UploadFile

from app.services.file_service import FileService
from app.core.config import settings


@pytest.fixture
def file_service():
    """
    FileService 인스턴스를 생성하는 fixture.
    이후 개별 테스트에서 내부 서비스들을 mock으로 교체한다.
    """
    return FileService()


@pytest.fixture
def patch_settings_dirs(monkeypatch, tmp_path):
    """
    테스트용 디렉터리로 settings 경로를 고정한다.
    """
    upload_dir = tmp_path / "uploads"
    processed_dir = tmp_path / "processed"
    upload_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(settings, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(settings, "ALLOWED_IMAGE_EXTENSIONS", {".png", ".jpg", ".jpeg"})
    monkeypatch.setattr(settings, "ALLOWED_PDF_EXTENSIONS", {".pdf"})

    return {"upload_dir": upload_dir, "processed_dir": processed_dir}


@pytest.mark.asyncio
async def test_save_upload_file_success(file_service, patch_settings_dirs, monkeypatch):
    """
    정상 업로드 파일 저장 테스트
    """
    # build_saved_filename 결과를 고정해서 예측 가능한 파일명으로 검증
    monkeypatch.setattr(
        "app.services.file_service.build_saved_filename",
        lambda filename: f"saved_{filename}"
    )

    upload = UploadFile(
        filename="sample.png",
        file=io.BytesIO(b"test-image-bytes")
    )

    result = await file_service.save_upload_file(upload)

    expected_path = patch_settings_dirs["upload_dir"] / "saved_sample.png"

    assert result == expected_path
    assert expected_path.exists()
    assert expected_path.read_bytes() == b"test-image-bytes"


@pytest.mark.asyncio
async def test_save_upload_file_raises_when_filename_empty(file_service, patch_settings_dirs):
    """
    filename이 비어 있을 때 HTTPException 400 검증
    """
    upload = UploadFile(
        filename="",
        file=io.BytesIO(b"dummy")
    )

    with pytest.raises(HTTPException) as exc_info:
        await file_service.save_upload_file(upload)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "filename is empty"


@pytest.mark.asyncio
async def test_save_upload_file_raises_when_content_empty(file_service, patch_settings_dirs, monkeypatch):
    """
    업로드 파일 내용이 비어 있을 때 HTTPException 400 검증
    """
    monkeypatch.setattr(
        "app.services.file_service.build_saved_filename",
        lambda filename: f"saved_{filename}"
    )

    upload = UploadFile(
        filename="empty.png",
        file=io.BytesIO(b"")
    )

    with pytest.raises(HTTPException) as exc_info:
        await file_service.save_upload_file(upload)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "uploaded file is empty"


def test_detect_file_type_returns_image_for_allowed_image_extension(file_service, patch_settings_dirs):
    """
    이미지 확장자 판별 테스트
    """
    result = file_service.detect_file_type("photo.png")
    assert result == "image"


def test_detect_file_type_returns_pdf_for_allowed_pdf_extension(file_service, patch_settings_dirs):
    """
    PDF 확장자 판별 테스트
    """
    result = file_service.detect_file_type("document.pdf")
    assert result == "pdf"


def test_detect_file_type_raises_for_unsupported_extension(file_service, patch_settings_dirs):
    """
    지원하지 않는 확장자 예외 테스트
    """
    with pytest.raises(HTTPException) as exc_info:
        file_service.detect_file_type("file.exe")

    assert exc_info.value.status_code == 400
    assert "unsupported file extension" in exc_info.value.detail


def test_process_file_image_success_without_db(file_service, patch_settings_dirs):
    """
    image 타입 처리 성공 테스트
    - image 전처리 호출
    - OCR 호출
    - extract_fields 호출
    - DB 저장 안 함
    """
    # Arrange
    test_file = Path("/tmp/input/sample.png")

    file_service.img_preprocess_service = Mock()
    file_service.ocr_service = Mock()
    file_service.extraction_service = Mock()
    file_service.db_service = Mock()
    file_service.pdf_preprocess_service = Mock()

    file_service.img_preprocess_service.preprocess_image.return_value = [
        "processed_1.png"
    ]
    file_service.ocr_service.run_ocr.return_value = {"ocr_text": "hello"}
    file_service.extraction_service.extract_fields.return_value = {"name": "kim"}

    # Act
    result = file_service.process_file(test_file, "image", save_to_db=False)

    # Assert
    file_service.img_preprocess_service.preprocess_image.assert_called_once_with(
        input_path=str(test_file),
        output_dir=str(settings.PROCESSED_DIR),
    )
    file_service.pdf_preprocess_service.preprocess_pdf.assert_not_called()

    file_service.ocr_service.run_ocr.assert_called_once_with("processed_1.png", "image")
    file_service.extraction_service.extract_fields.assert_called_once_with({"ocr_text": "hello"})
    file_service.db_service.save_document_result.assert_not_called()

    assert result["filename"] == "sample.png"
    assert result["file_type"] == "image"
    assert result["saved_path"] == str(test_file)
    assert result["preprocess_target"] == "image"
    assert result["extracted_data"] == {"name": "kim"}
    assert result["db_saved"] is False
    assert result["db_message"] is None


def test_process_file_pdf_success_with_db(file_service, patch_settings_dirs):
    """
    pdf 타입 처리 성공 + DB 저장 테스트
    """
    # Arrange
    test_file = Path("/tmp/input/sample.pdf")

    file_service.img_preprocess_service = Mock()
    file_service.pdf_preprocess_service = Mock()
    file_service.ocr_service = Mock()
    file_service.extraction_service = Mock()
    file_service.db_service = Mock()

    file_service.pdf_preprocess_service.preprocess_pdf.return_value = [
        "page_1.png"
    ]
    file_service.ocr_service.run_ocr.return_value = {"ocr_text": "invoice no 1"}
    file_service.extraction_service.extract_fields.return_value = {"invoice_no": "1"}
    file_service.db_service.save_document_result.return_value = "saved to db"

    # Act
    result = file_service.process_file(test_file, "pdf", save_to_db=True)

    # Assert
    file_service.pdf_preprocess_service.preprocess_pdf.assert_called_once_with(
        input_path=str(test_file),
        output_dir=str(settings.PROCESSED_DIR),
    )
    file_service.img_preprocess_service.preprocess_image.assert_not_called()

    file_service.ocr_service.run_ocr.assert_called_once_with("page_1.png", "pdf")
    file_service.extraction_service.extract_fields.assert_called_once_with({"ocr_text": "invoice no 1"})

    file_service.db_service.save_document_result.assert_called_once_with(
        filename="sample.pdf",
        file_type="pdf",
        saved_path=str(test_file),
        extracted_json={"invoice_no": "1"},
    )

    assert result["db_saved"] is True
    assert result["db_message"] == "saved to db"
    assert result["extracted_data"] == {"invoice_no": "1"}


def test_process_file_raises_for_invalid_file_type(file_service, patch_settings_dirs):
    """
    잘못된 file_type 입력 시 HTTPException 400 검증
    """
    test_file = Path("/tmp/input/unknown.bin")

    with pytest.raises(HTTPException) as exc_info:
        file_service.process_file(test_file, "binary", save_to_db=False)

    assert exc_info.value.status_code == 400
    assert "invalid file type" in exc_info.value.detail


def test_process_file_multiple_preprocessed_outputs_keeps_only_last_result(file_service, patch_settings_dirs):
    """
    현재 구현 기준:
    여러 전처리 결과가 있어도 마지막 extracted_data만 반환되는 동작을 검증한다.
    이 테스트는 설계 결함을 드러내는 문서화 테스트 역할도 한다.
    """
    test_file = Path("/tmp/input/sample.pdf")

    file_service.pdf_preprocess_service = Mock()
    file_service.img_preprocess_service = Mock()
    file_service.ocr_service = Mock()
    file_service.extraction_service = Mock()
    file_service.db_service = Mock()

    file_service.pdf_preprocess_service.preprocess_pdf.return_value = [
        "page_1.png",
        "page_2.png",
    ]

    file_service.ocr_service.run_ocr.side_effect = [
        {"ocr_text": "first"},
        {"ocr_text": "second"},
    ]

    file_service.extraction_service.extract_fields.side_effect = [
        {"page": 1, "value": "A"},
        {"page": 2, "value": "B"},
    ]

    result = file_service.process_file(test_file, "pdf", save_to_db=False)

    assert file_service.ocr_service.run_ocr.call_count == 2
    assert file_service.extraction_service.extract_fields.call_count == 2

    # 현재 코드는 마지막 extracted_data만 반환한다.
    assert result["extracted_data"] == {"page": 2, "value": "B"}