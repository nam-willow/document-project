from pathlib import Path
from fastapi import HTTPException, UploadFile

from app.core.config import settings
from app.core.logging import get_logger
from app.services.pdf_preprocess_service import PdfPreprocessService
from app.services.img_preprocess_service import ImgPreprocessService
# from app.services.ocr_service import OCRService
from app.services.ocr_service_easyocr import OCRService as EasyOCRService
from app.services.extraction_service import ExtractionService
from app.services.db_service import DBService
from app.utils.file_utils import get_extension, build_saved_filename

from app.ml.easyocr_predictor import EasyOCRPredictor

logger = get_logger(__name__)


class FileService:
    def __init__(self) -> None:
        self.img_preprocess_service = ImgPreprocessService()
        self.pdf_preprocess_service = PdfPreprocessService()
        # self.ocr_service = OCRService()
        self.ocr_service_easyocr = EasyOCRService()
        self.extraction_service = ExtractionService()
        self.db_service = DBService()

    async def save_upload_file(self, upload_file: UploadFile) -> Path:
        """
        업로드 파일을 디스크에 저장.
        """
        print("file_service.save_upload_file called | filename=%s", upload_file.filename)
        if not upload_file.filename:
            raise HTTPException(status_code=400, detail="filename is empty")

        saved_filename = build_saved_filename(upload_file.filename)
        saved_path = settings.UPLOAD_DIR / saved_filename
        print("파일 저장할 경로는 %s 입니다", saved_path)

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
        print("detect_file_type called | filename=%s", filename)
        ext = get_extension(filename)

        if ext in settings.ALLOWED_IMAGE_EXTENSIONS:
            return "image"
        if ext in settings.ALLOWED_PDF_EXTENSIONS:
            return "pdf"

        raise HTTPException(status_code=400, detail=f"unsupported file extension: {ext}")

    def process_file(self, predictor: EasyOCRPredictor, file_path: Path, file_type: str, save_to_db: bool = False) -> dict:
        """
        파일 타입에 따라 전처리 -> OCR -> 추출 -> (선택) DB 저장.
        """
        print("파일 확장자에 따라 전처리 구분 로직) | file_path=%s, file_type=%s", file_path, file_type)
        logger.info("Processing started | file_type=%s | file_path=%s", file_type, file_path)

        if file_type == "image":
            print("str(settings.PROCESSED_DIR): ", str(settings.PROCESSED_DIR))
            preprocessed_path = self.img_preprocess_service.preprocess_image(input_path=str(file_path), output_dir=str(settings.PROCESSED_DIR))
        elif file_type == "pdf":
            print("str(settings.PROCESSED_DIR): ", str(settings.PROCESSED_DIR))
            preprocessed_path = self.pdf_preprocess_service.preprocess_pdf(input_path=str(file_path), output_dir=str(settings.PROCESSED_DIR))
        else:
            raise HTTPException(status_code=400, detail=f"invalid file type: {file_type}")

        print("전처리 끝났으니까 OCR 실행할게요) | preprocessed_path=%s", preprocessed_path)
        logger.info("Preprocessing finished | preprocessed_path=%s", preprocessed_path)

        # EasyOCR로 OCR 실행
        ocr_result = self.ocr_service_easyocr.run_ocr(predictor, preprocessed_path)

        print("OCR 끝났으니까 필드 추출 실행할게요) | ocr_result=%s", ocr_result)
        extracted_data = self.extraction_service.extract_fields(ocr_result)

        db_saved = False
        db_message = None

        if save_to_db:
            for item in extracted_data:
                print(f"extracted_data item: {item}")
                db_message = self.db_service.save_document_result(
                    filename=file_path.name,
                    file_type=file_type,
                    saved_path=str(file_path),
                    extracted_json=item,
                )
            
            db_saved = True

        else:
            print("DB 저장은 하지 않을게요)")

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