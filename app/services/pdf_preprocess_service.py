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
    SIZE_THRESHOLD = 15.0   # 글자 크기(size) 삭제 기준 크기, 이것보다 크면 제거
    PAD = 1                 # bbox 여유 포인트, 텍스트 삭제 시 텍스트 크기 + PAD 크기 만큼 제거

    MAX_DELETE_RATIO = 0.30 # 삭제 대상 텍스트가 전체의 n% 넘으면 삭제 진행하지 않음
    MAX_DELETE_COUNT = 80   # 삭제 대상 텍스트가 너무 많으면 삭제 진행하지 않음

    PERCENTILE_GUARD = 95   # 전체 텍스트 중 가장 큰 크기를 대상으로 지정 (가장 큰 텍스트를 100으로 잡고 100-n을 삭제 대상으로 지정)
    MIN_P95 = 10.0          # PERCENTILE_GUARD의 가장 작은 텍스트 크기가 n미만이면 삭제 진행하지 않음

    MIN_TEXT_LEN = 1        # 빈 span 제외용

    ###################### 수정이 필요함  ######################
    pdf_in = r"C:\Users\yjcho\Documents\UiPath\RPA_SR_03_WriteResultFile_BOX - 추출 테스트\pdf_crop\EP-DX310JBRGRU_DLC_UNIT BOX.pdf"
    pdf_out = pdf_in.replace(".pdf", "(rm_ver2).pdf")



    # def preprocess_pdf(self, file_path: str, output_path: str,dry_run: bool = False) -> str:
    #     logger.info("PDF preprocessing started: %s", file_path)
    #     # TODO: PDF 전처리 로직 구현
    #     print("PDF preprocessing started: %s", file_path) 


    def expand(r: fitz.Rect, pad: float) -> fitz.Rect:
        return fitz.Rect(r.x0-pad, r.y0-pad, r.x1+pad, r.y1+pad)


    def percentile(vals, p):
        vals = sorted(vals)
        if not vals:
            return None

        k = (len(vals)-1) * (p / 100.0)
        f = int(k)
        c = min(f+1, len(vals)-1)

        if f == c:
            return vals[f]

        return vals[f] + (vals[c] - vals[f]) * (k-f)


    if __name__ == "__main__":
        print("start")

        input_dir = r"N:\사용자폴더\전달파일\MX_BOX\file_3"
        output_dir = r"N:\사용자폴더\전달파일\MX_BOX\pdf_txt_rm"

        folder = Path(input_dir)
        files = sorted([p for p in folder.iterdir() if p.is_file()])
        total_files = len(files)

        for i, filename in enumerate(files, start=1):
            print(f"[{i}/{total_files}] 처리중: {filename.name}")

            pdf_in = os.path.join(input_dir, filename.name)
            pdf_out = os.path.join(output_dir, filename.name.replace(".pdf", "(rm_ver2).pdf"))

            doc = fitz.open(pdf_in)

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
                            if len(txt) < MIN_TEXT_LEN:
                                continue

                            size = float(span.get("size", 0))
                            rect = fitz.Rect(span["bbox"])
                            sizes.append(size)
                            spans_info.append((size, rect, txt))

                if not spans_info:
                    continue

                # 2) 퍼센타일 가드: 이 페이지에 진짜 큰 글자가 있는지 확인
                pval = percentile(sizes, PERCENTILE_GUARD)
                if pval is None or pval < MIN_P95:
                    # 페이지에 큰 글자가 없다면 삭제 진행하지 않음
                    continue

                # 3) 삭제 후보 만들기
                candidates = []
                for size, rect, txt in spans_info:
                    if size > SIZE_THRESHOLD:
                        candidates.append(expand(rect, PAD))

                if not candidates:
                    continue

                # 4) 과삭제 방지 (삭제할 텍스트 비율/개수 확인)
                total_spans = len(spans_info)
                delete_ratio = len(candidates) / total_spans

                if delete_ratio > MAX_DELETE_RATIO:
                    continue
                if len(candidates) > MAX_DELETE_COUNT:
                    continue

                # 5) 덩어리 병합 없이 span 하나씩 제거
                for r in candidates:
                    page.add_redact_annot(r, fill=(1,1,1))
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)

            doc.save(pdf_out, garbage=4, deflate=True)
            doc.close()

        print("end")