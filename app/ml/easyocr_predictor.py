"""
EasyOCRPredictor: 줄글 문서 이미지에서 텍스트를 추출하는 Wrapper.

STR benchmark 대체 모듈.
한글/영어 문서 한 장 전체를 처리할 수 있다.

지원 입력:
  - 파일 경로 (str, Path)
  - PIL Image
  - numpy array
"""

import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union

import numpy as np
import torch
import cv2
import easyocr
from PIL import Image

torch.set_num_threads(1)
cv2.setNumThreads(0)

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """
    단일 문서 OCR 결과.
    
    Attributes:
        text:       전체 텍스트 (줄바꿈 포함)
        lines:      줄 단위 텍스트 리스트
        confidence: 전체 평균 신뢰도 (0.0 ~ 1.0)
        elapsed_ms: 추론 소요 시간(ms)
    """
    text: str
    lines: List[str]
    confidence: float
    elapsed_ms: float


class EasyOCRPredictor:
    """
    EasyOCR 기반 문서 텍스트 추출기.
    
    사용 예:
        predictor = EasyOCRPredictor(lang=["ko", "en"])
        result = predictor.predict("path/to/document.png")
        print(result.text)
    """

    def __init__(
        self,
        lang: List[str] = ["ko", "en"],  # 한글 + 영어
        use_gpu: bool = False,            # GPU 없으면 False
    ):
        logger.info("EasyOCR 초기화 | lang=%s | gpu=%s", lang, use_gpu)
        # 첫 실행 시 모델 자동 다운로드 (~500MB)
        self.reader = easyocr.Reader(lang, gpu=use_gpu)
        logger.info("EasyOCR 초기화 완료")

    def predict(self, image: Union[str, Path, np.ndarray, Image.Image]) -> OCRResult:
        """
        문서 이미지 한 장에서 텍스트를 추출한다.

        Args:
            image: 파일경로(str/Path), PIL Image, numpy array 중 하나

        Returns:
            OCRResult(text, lines, confidence, elapsed_ms)

        Example:
            >>> predictor = EasyOCRPredictor()
            >>> result = predictor.predict("/tmp/document.png")
            >>> print(result.text)
            '홍길동은 조선시대...'
        """
        t0 = time.perf_counter()

        # ── 입력 타입 정규화 ─────────────────────────────────────────────
        img_input = self._to_input(image)
        logger.info("입력 타입 정규화") 

        # ── EasyOCR 추론 ─────────────────────────────────────────────────
        # 반환: [([좌표], "텍스트", confidence), ...]
        raw_results = self.reader.readtext(img_input)
        logger.info("EasyOCR 추론 완료") 

        if not raw_results:
            logger.warning("OCR 결과 없음 | image=%s", image)
            return OCRResult(text="", lines=[], confidence=0.0, elapsed_ms=0.0)

        # ── 결과 정리 ────────────────────────────────────────────────────
        lines = [text for (_, text, conf) in raw_results if conf > 0.3]
        confidences = [conf for (_, _, conf) in raw_results]
        logger.info("결과 정리 ") 

        full_text = "\n".join(lines)
        avg_confidence = round(sum(confidences) / len(confidences), 4)
        elapsed = round((time.perf_counter() - t0) * 1000, 2)

        logger.info(
            "OCR 완료 | lines=%d | confidence=%.4f | elapsed=%.1fms",
            len(lines), avg_confidence, elapsed
        )

        return OCRResult(
            text=full_text,
            lines=lines,
            confidence=avg_confidence,
            elapsed_ms=elapsed,
        )

    def _to_input(self, image: Union[str, Path, np.ndarray, Image.Image]):
        """EasyOCR이 받을 수 있는 형태로 변환."""
        if isinstance(image, (str, Path)):
            path = Path(image)
            if not path.exists():
                raise FileNotFoundError(f"이미지 파일 없음: {path}")
            return str(path)  # EasyOCR은 경로 문자열 직접 지원

        if isinstance(image, Image.Image):
            return np.array(image)  # PIL → numpy

        if isinstance(image, np.ndarray):
            return image

        raise ValueError(f"지원하지 않는 타입: {type(image)}")