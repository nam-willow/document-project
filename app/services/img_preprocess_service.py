from app.core.logging import get_logger
import fitz  # PyMuPDF
import math
from pathlib import Path
from statistics import median
from typing import Any

logger = get_logger(__name__)


class ImgPreprocessService:
    """
    파일 유형별 전처리 분기.
    실제 이미지/PDF 전처리는 나중에 구현 예정.
    """

    def preprocess_image(self, file_path: str) -> str:
        logger.info("Image preprocessing started: %s", file_path)
        # TODO: 이미지 전처리 로직 구현
        print("Image preprocessing started: %s", file_path)
        return file_path

