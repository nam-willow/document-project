from fastapi import FastAPI

from app.api.v1.file_api import router as file_router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

app.include_router(file_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}