from fastapi import FastAPI
from app.api.v1.file_api import router as document_router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

app.include_router(document_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
