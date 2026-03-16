from pathlib import Path
from fastapi import HTTPException, UploadFile

from app.core.config import settings
from app.core.logging import get_logger
from app.services.preprocess_service import PreprocessService
from app.services.ocr_service import OCRService
from app.services.extraction_service import ExtractionService
from app.services.db_service import DBService
from app.utils.file_utils import get_extension, build_saved_filename

logger = get_logger(__name__)


class FileService:
    def __init__(self) -> None:
        self.preprocess_service = PreprocessService()
        self.ocr_service = OCRService()
        self.extraction_service = ExtractionService()
        self.db_service = DBService()

    async def save_upload_file(self, upload_file: UploadFile) -> Path:
        """
        업로드 파일을 디스크에 저장.
        """
        if not upload_file.filename:
            raise HTTPException(status_code=400, detail="filename is empty")

        saved_filename = build_saved_filename(upload_file.filename)
        saved_path = settings.UPLOAD_DIR / saved_filename

        content = await upload_file.read()
        if not content:
            raise HTTPException(status_code=400, detail="uploaded file is empty")

        with open(saved_path, "wb") as f:
            f.write(content)

        logger.info("File saved | original=%s | saved=%s", upload_file.filename, saved_path)
        return saved_path

    def detect_file_type(self, filename: str) -> str:
        """
        파일 확장자를 기준으로 image / pdf 판별.
        """
        ext = get_extension(filename)

        if ext in settings.ALLOWED_IMAGE_EXTENSIONS:
            return "image"
        if ext in settings.ALLOWED_PDF_EXTENSIONS:
            return "pdf"

        raise HTTPException(status_code=400, detail=f"unsupported file extension: {ext}")

    def process_file(self, file_path: Path, file_type: str, save_to_db: bool = False) -> dict:
        """
        파일 타입에 따라 전처리 -> OCR -> 추출 -> (선택) DB 저장.
        """
        logger.info("Processing started | file_type=%s | file_path=%s", file_type, file_path)

        if file_type == "image":
            preprocessed_path = self.preprocess_service.preprocess_image(str(file_path))
        elif file_type == "pdf":
            preprocessed_path = self.preprocess_service.preprocess_pdf(str(file_path))
        else:
            raise HTTPException(status_code=400, detail=f"invalid file type: {file_type}")

        ocr_result = self.ocr_service.run_ocr(preprocessed_path, file_type)
        extracted_data = self.extraction_service.extract_fields(ocr_result)

        db_saved = False
        db_message = None

        if save_to_db:
            db_message = self.db_service.save_document_result(
                filename=file_path.name,
                file_type=file_type,
                saved_path=str(file_path),
                extracted_json=extracted_data,
            )
            db_saved = True

        logger.info("Processing finished | file_path=%s", file_path)

        return {
            "filename": file_path.name,
            "file_type": file_type,
            "saved_path": str(file_path),
            "preprocess_target": file_type,
            "extracted_data": extracted_data,
            "db_saved": db_saved,
            "db_message": db_message,
        }