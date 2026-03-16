from typing import Any, Dict, Optional
from pydantic import BaseModel


class UploadResponse(BaseModel):
    """
    업로드 및 처리 결과를 반환하는 모델.(임시)
     - filename: 업로드된 파일 이름
     - file_type: 파일 유형 (예: "image/jpeg", "application/pdf")
     - saved_path: 저장된 파일 경로
     - preprocess_target: 전처리 대상 (예: "ocr", "table_extraction")
     - extracted_data: 추출된 데이터 (예: OCR 결과, 테이블 데이터)
     - db_saved: DB 저장 여부
     - db_message: DB 저장 결과 메시지 (성공/실패 이유 등)
    """
    filename: str
    file_type: str
    saved_path: str
    preprocess_target: str
    extracted_data: Dict[str, Any]
    db_saved: bool
    db_message: Optional[str] = None