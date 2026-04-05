from fastapi import APIRouter, Request, File, Form, UploadFile

from app.models.response_models import UploadResponse
from app.services.file_service import FileService

router = APIRouter(prefix="/api/v1/files", tags=["files"])
file_service = FileService()


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    save_to_db: bool = Form(default=False),
):
    """
    파일 업로드 API.
    - 이미지 / PDF 분기
    - 전처리 -> OCR -> 필드 추출
    - 필요 시 DB 저장
    """
    print("/upload api called | filename=%s, save_to_db=%s", file.filename, save_to_db)

    # Step 1: FastAPI의 lifespan에서 로드한 STRPredictor 인스턴스 가져오기
    predictor = request.app.state.predictor  

    # Step 2: 파일 저장
    saved_path = await file_service.save_upload_file(file)
    
    # Step 3: 파일 타입 감지
    file_type = file_service.detect_file_type(file.filename)
    print("file type detected | file_type=%s", file_type)

    # Step 4: 파일 처리 (전처리 -> OCR -> 필드 추출 -> DB 저장)
    result = file_service.process_file(
        predictor=predictor,
        file_path=saved_path,
        file_type=file_type,
        save_to_db=save_to_db,
    )
    return result