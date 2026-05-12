from app.core.logging import get_logger
import fitz  # PyMuPDF
import math
from pathlib import Path
from statistics import median
from typing import Any, List
import os

logger = get_logger(__name__)



class PdfPreprocessService:
    # =====================
    # 설정
    # =====================
    
    def __init__(self):
        self.SIZE_THRESHOLD = 15.0   # 글자 크기(size) 삭제 기준 크기, 이것보다 크면 제거
        self.PAD = 1                 # bbox 여유 포인트, 텍스트 삭제 시 텍스트 크기 + PAD 크기 만큼 제거

        self.MAX_DELETE_RATIO = 0.30 # 삭제 대상 텍스트가 전체의 n% 넘으면 삭제 진행하지 않음
        self.MAX_DELETE_COUNT = 80   # 삭제 대상 텍스트가 너무 많으면 삭제 진행하지 않음

        self.PERCENTILE_GUARD = 95   # 전체 텍스트 중 가장 큰 크기를 대상으로 지정 (가장 큰 텍스트를 100으로 잡고 100-n을 삭제 대상으로 지정)
        self.MIN_P95 = 10.0          # PERCENTILE_GUARD의 가장 작은 텍스트 크기가 n미만이면 삭제 진행하지 않음

        self.MIN_TEXT_LEN = 1        # 빈 span 제외용



    def expand(self, r: fitz.Rect, pad: float) -> fitz.Rect:
        return fitz.Rect(r.x0-pad, r.y0-pad, r.x1+pad, r.y1+pad)


    def percentile(self, vals, p):
        vals = sorted(vals)
        if not vals:
            return None

        k = (len(vals)-1) * (p / 100.0)
        f = int(k)
        c = min(f+1, len(vals)-1)

        if f == c:
            return vals[f]

        return vals[f] + (vals[c] - vals[f]) * (k-f)


    def preprocess_pdf(self, input_path: str, output_dir: str) -> list:

        input_path = Path(input_path)

        output_dir_product = os.path.join(output_dir, input_path.name)
        os.makedirs(output_dir_product, exist_ok=True)

        pdf_out = os.path.join(output_dir_product, input_path.name.replace(".pdf", "(rm_ver2).pdf"))
        print("output_dir_product: ", output_dir_product)

        doc = fitz.open(input_path)

        for page in doc:
            d = page.get_text("dict")

            sizes = []
            spans_info = [] # (size, rect, text)

            # 1) span 수집 + size 분포 만들기
            for block in d.get("blocks", []):
                if block.get("type") != 0:
                    continue

                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        txt = (span.get("text") or "").strip()
                        if len(txt) < self.MIN_TEXT_LEN:
                            continue

                        size = float(span.get("size", 0))
                        rect = fitz.Rect(span["bbox"])
                        sizes.append(size)
                        spans_info.append((size, rect, txt))

            if not spans_info:
                continue

            # 2) 퍼센타일 가드: 이 페이지에 진짜 큰 글자가 있는지 확인
            pval = self.percentile(sizes, self.PERCENTILE_GUARD)
            if pval is None or pval < self.MIN_P95:
                # 페이지에 큰 글자가 없다면 삭제 진행하지 않음
                continue

            # 3) 삭제 후보 만들기
            candidates = []
            for size, rect, txt in spans_info:
                if size > self.SIZE_THRESHOLD:
                    candidates.append(self.expand(rect, self.PAD))

            if not candidates:
                continue

            # 4) 과삭제 방지 (삭제할 텍스트 비율/개수 확인)
            total_spans = len(spans_info)
            delete_ratio = len(candidates) / total_spans

            if delete_ratio > self.MAX_DELETE_RATIO:
                continue
            if len(candidates) > self.MAX_DELETE_COUNT:
                continue

            # 5) 덩어리 병합 없이 span 하나씩 제거
            for r in candidates:
                page.add_redact_annot(r, fill=(1,1,1))
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)

        doc.save(pdf_out, garbage=4, deflate=True)
        doc.close()

        print("end")
        return [pdf_out]


class PdfToImgPreprocessService:
    """
    PDF → 페이지별 이미지 변환 → ImgBackgroundPreprocess 전처리 파이프라인.

    preprocess_pdf()는 FileService 인터페이스와 호환되도록
    전처리된 이미지 경로 리스트를 반환한다.
    """

    DPI = 200  # PDF 렌더링 해상도

    def __init__(self):
        from app.services.img_preprocess_service import ImgBackgroundPreprocess
        self.img_preprocess = ImgBackgroundPreprocess()

    def _render_pdf_to_images(self, input_path: str, images_dir: str) -> List[str]:
        """PDF 각 페이지를 PNG로 렌더링하여 저장하고 경로 리스트 반환."""
        doc = fitz.open(input_path)
        mat = fitz.Matrix(self.DPI / 72, self.DPI / 72)
        saved = []

        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=mat, alpha=False)
            page_path = os.path.join(images_dir, f"page_{i+1:03d}.png")
            pix.save(page_path)
            saved.append(page_path)
            logger.info("페이지 렌더링 완료 | page=%d | path=%s", i + 1, page_path)

        doc.close()
        return saved

    def preprocess_pdf(self, input_path: str, output_dir: str) -> List[str]:
        """
        PDF → 이미지 변환 → 이미지 전처리 → 전처리 결과 경로 리스트 반환.
        FileService.process_file()에서 pdf 분기 시 호출된다.
        """
        input_path = Path(input_path)
        stem = input_path.stem

        product_dir = os.path.join(output_dir, stem)
        images_dir = os.path.join(product_dir, "pages")
        os.makedirs(images_dir, exist_ok=True)

        logger.info("PDF → 이미지 변환 시작 | input=%s", input_path)
        page_paths = self._render_pdf_to_images(str(input_path), images_dir)
        logger.info("PDF → 이미지 변환 완료 | 페이지 수=%d", len(page_paths))

        preprocessed = []
        for page_path in page_paths:
            try:
                result = self.img_preprocess.preprocess_image(
                    input_path=page_path,
                    output_dir=product_dir,
                )
                preprocessed.extend(result)
                logger.info("이미지 전처리 완료 | page=%s", page_path)
            except Exception as e:
                logger.error("이미지 전처리 실패, 원본 이미지 사용 | page=%s | error=%s", page_path, e)
                preprocessed.append(page_path)

        return preprocessed