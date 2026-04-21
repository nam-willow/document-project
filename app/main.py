from fastapi import FastAPI
from app.api.v1.file_api import router as file_router
from app.core.config import settings

from contextlib import asynccontextmanager
from app.ml.deep_text_recognition_benchmark.str_predictor import STRPredictor

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 1회만 모델 로드
    app.state.predictor = STRPredictor(
        saved_model="app/ml/deep_text_recognition_benchmark/saved_models/TPS-ResNet-BiLSTM-Attn.pth"
    )
    yield
    # 서버 종료 시 정리 (필요하면)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.include_router(file_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}