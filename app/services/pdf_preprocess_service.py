from app.core.logging import get_logger
import fitz  # PyMuPDF
import math
from pathlib import Path
from statistics import median
from typing import Any

logger = get_logger(__name__)



class PdfPreprocessService:

    def preprocess_pdf(self, file_path: str, output_path: str,dry_run: bool = False) -> str:
            logger.info("PDF preprocessing started: %s", file_path)
            # TODO: PDF 전처리 로직 구현
            print("PDF preprocessing started: %s", file_path) 