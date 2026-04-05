from pathlib import Path


class Settings:
    """
    애플리케이션 전역 설정.
    운영에서는 pydantic-settings 또는 환경변수 기반으로 확장 권장.
    """
    APP_NAME = "Document OCR API"
    APP_VERSION = "0.1.0"

    BASE_DIR = Path(__file__).resolve().parent.parent
    STORAGE_DIR = BASE_DIR / "storage"
    UPLOAD_DIR = STORAGE_DIR / "uploads"
    PROCESSED_DIR = STORAGE_DIR / "processed"
    REPO_PATH = BASE_DIR / "ml" / "deep-text-recognition-benchmark-master"


    # 허용 확장자
    ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    ALLOWED_PDF_EXTENSIONS = {".pdf"}

    # 추후 실제 DB 연결 문자열로 교체
    DATABASE_URL = "mysql+pymysql://user:password@localhost:3306/app_db"

    # 추후 ML Skill 연결용 설정 경로
    ML_SKILL_DIR = BASE_DIR / "ml_skill"
    ML_SKILL_CONFIG_PATH = ML_SKILL_DIR / "config" / "model_config.example.json"




settings = Settings()

# 시작 시 필요한 디렉터리 생성
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)