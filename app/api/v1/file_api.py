from fastapi import APIRouter, File, UploadFile
from celery.result import AsyncResult

from app.models.response_models import JobAcceptedResponse, JobResultResponse
from app.services.file_service import FileService
from app.tasks.document_task import process_document_task
from app.worker import celery_app

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

_file_service = FileService()

_CELERY_STATE_MAP = {
    "PENDING": "queued",
    "STARTED": "processing",
    "RETRY":   "processing",
}


@router.post("/process", response_model=JobAcceptedResponse)
async def process_document(file: UploadFile = File(...)):
    """
    영수증 이미지/PDF 업로드 → 큐 적재 → job_id 즉시 반환

    처리 흐름: 전처리 → OCR → AI 필드 추출
    결과는 GET /api/v1/documents/{job_id}/result 로 조회
    """
    saved_path = await _file_service.save_upload_file(file)
    file_type = _file_service.detect_file_type(file.filename)

    task = process_document_task.delay(str(saved_path), file_type)
    print( "작업이 큐에 적재되었습니다 | job_id=%s", task.id)
    return JobAcceptedResponse(
        job_id=task.id,
        status="queued",
        message="접수됐습니다. job_id로 결과를 조회하세요.",
    )


@router.get("/{job_id}/result", response_model=JobResultResponse)
def get_result(job_id: str):
    """
    job_id로 처리 결과 조회

    status 값:
    - queued     : 대기 중
    - processing : 처리 중
    - done       : 완료
    - failed     : 실패
    """
    task = AsyncResult(job_id, app=celery_app)

    if task.state == "SUCCESS":
        return JobResultResponse(job_id=job_id, status="done", result=task.result)
    if task.state == "FAILURE":
        return JobResultResponse(job_id=job_id, status="failed", error=str(task.result))

    return JobResultResponse(
        job_id=job_id,
        status=_CELERY_STATE_MAP.get(task.state, task.state.lower()),
    )
