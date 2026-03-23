from app.core.logging import get_logger
import fitz  # PyMuPDF
import math
from pathlib import Path
from statistics import median
from typing import Any
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