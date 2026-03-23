from app.core.logging import get_logger
import fitz  # PyMuPDF
import math
from pathlib import Path
from statistics import median
from typing import Any
import cv2
import numpy as np
import os
from datetime import datetime
from app.utils.file_utils import imread_unicode, imwrite_unicode, test_image_save

logger = get_logger(__name__)


class ImgPreprocessService:

    """
    파일 유형별 전처리 분기.
    실제 이미지/PDF 전처리는 나중에 구현 예정.
    """

    # def preprocess_image(self, file_path: str, output_dir: str) -> str:
    #     logger.info("Image preprocessing started: %s", file_path)
    #     # TODO: 이미지 전처리 로직 구현
    #     print("Image preprocessing started: %s", file_path)
    #     return file_path


    def black_background_trim(self, img_path: str, out_dir: str, png_filename: str, is_test: bool):

        img = imread_unicode(img_path)
        test_image_save(out_dir, "background", "0-1.원본.png", img, is_test)

        H, W = img.shape[:2]
        canvas_w = W + 100
        canvas_h = H + 100

        canvas = np.full((canvas_h, canvas_w, 3), (0, 0, 0), dtype=np.uint8)
        print(f"canvas.shape:{canvas.shape}")
        test_image_save(out_dir, "background", "0-2.canvas_0.png", canvas, is_test)

        Hc, Wc = canvas.shape[:2]
        Hi, Wi = img.shape[:2]
        x0 = (Wc - Wi) // 2
        y0 = (Hc - Hi) // 2

        canvas[y0:y0 + Hi, x0:x0 + Wi] = img
        img = canvas
        test_image_save(out_dir, "background", "0-3.canvas_total.png", img, is_test)

        max_size = max(H, W)
        if max_size > 7000:
            print("******리사이즈 진행")
            H, W = img.shape[:2]
            max_size = max(H, W)
            print(max_size)

            scale = 7000 / max_size
            print(f" - scale: {scale}")
            new_w = int(round(W * scale))
            new_h = int(round(H * scale))

            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

        origin_img = img.copy()

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        test_image_save(out_dir, "background", "01_gray.png", gray, is_test)

        gray = cv2.GaussianBlur(gray, (7, 7), 0)
        test_image_save(out_dir, "background", "02_blured.png", gray, is_test)

        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8), iterations=2)
        test_image_save(out_dir, "background", "03_morphologyEx.png", th, is_test)

        edged = cv2.Canny(th, 100, 100)
        test_image_save(out_dir, "background", "04_canny.png", edged, is_test)

        edged = cv2.dilate(edged, None, iterations=9)
        test_image_save(out_dir, "background", "05_dilated.png", edged, is_test)

        padded = cv2.copyMakeBorder(edged, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=0)
        test_image_save(out_dir, "background", "06_padded.png", padded, is_test)

        flood = padded.copy()
        ff_mask = np.zeros((padded.shape[0] + 2, padded.shape[1] + 2), np.uint8)
        cv2.floodFill(flood, ff_mask, seedPoint=(0, 0), newVal=128)
        test_image_save(out_dir, "background", "07_flood.png", flood, is_test)

        inside = np.where(flood != 128, 255, 0).astype(np.uint8)

        inside = inside[2:-2, 2:-2]
        test_image_save(out_dir, "background", "07_mask.png", inside, is_test)

        kernel = np.ones((13, 13), np.uint8)
        inside = cv2.erode(inside, kernel, iterations=3)
        test_image_save(out_dir, "background", "08_erode.png", inside, is_test)

        if inside is None:
            raise ValueError("mask is none")

        if inside.ndim != 2:
            raise ValueError("mask must be single-channel (h,w)")

        outside_candidate = (inside == 0).astype(np.uint8) * 255

        _, m = cv2.threshold(inside, 0, 255, cv2.THRESH_BINARY)
        test_image_save(out_dir, "background", "09_THRESH_BINARY.png", m, is_test)

        ys, xs = np.where(m > 0)

        if xs.size < 500:
            print(" - 객체가 작음")

        H, W = m.shape[:2]
        x1, x2 = xs.min(), xs.max()
        y1, y2 = ys.min(), ys.max()

        padding = 20
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(W - 1, x2 + padding)
        y2 = min(H - 1, y2 + padding)

        cond = (m == 0)
        img[cond] = 255
        test_image_save(out_dir, "background", "9_fill_outside_white_0.png", img, is_test)

        mh, mw = m.shape[:2]
        pad = 10
        y_top_end = max(0, min(mh, y1 + pad))
        y_bottom_start = max(0, min(mh, y2 + pad))
        x_left_end = max(0, min(mw, x1 + pad))
        x_right_start = max(0, min(mw, x2 - pad))

        out = img.copy()

        def _paint(region_slice):
            print("region_slice: ", region_slice)
            if out.ndim == 2:
                out[region_slice] = 255
            else:
                out[region_slice] = (255, 255, 255)

        _paint((slice(0, y_top_end), slice(0, mw)))
        _paint((slice(y_bottom_start, mh), slice(0, mw)))
        _paint((slice(0, mh), slice(0, x_left_end)))
        _paint((slice(0, mh), slice(x_right_start, mw)))

        img = out

        cropped = img[y1:y2+1, x1:x2+1]
        origin_cropped = origin_img[y1:y2+1, x1:x2+1]

        return cropped, origin_cropped


    # 배경 잘라낸 png 이미지에서 문단 별 잘라내기
    def crop_paragraphs(
        self, img,
        origin_img,
        out_dir: str,
        png_filename: str,

        # -- binarization --
        binarize_mode: str,

        # -- morphology ( 문단 덩어리로 붙이기 ) --
        dilate_x_ratio: float,   # 이미지 너비 대비 가로 커널 비율
        dilate_y_ratio: float,   # 이미지 너비 대비 세로 커널 비율
        dilate_iter: int,

        # -- filtering --
        min_area_ratio: float,   # 전체 면적 대비 최소 문단 박스 비율
        min_w_ratio: float,      # 이미지 너비 대비 최소 박스 너비 비율
        min_h_ratio: float,      # 이미지 높이 대비 최소 박스 높이 비율

        # -- post --
        pad: int,
        sort_mode: str,
        kernel_mode: str,
        is_test:bool ):

        if img is None:
            # raise ValueError(f"Failed to read: {image_path}")
            raise ValueError(f"Failed to read")

        ########################################## 캔버스 붙이기 ##########################################
        H, W = img.shape[:2]

        # 1) grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        test_image_save(out_dir, "paragraphs", "1_gray.png", gray, is_test)

        # 2) binarize (글자= 흰색, 배경=검정)
        # THRESH_BINARY_INV 임계값 기준으로 반대로 색 변환 (배경검사일때 사용함)
        # THRESH_BINARY 임계값 기준 초과면 색 변환 (배경0들일때 사용함)
        if binarize_mode == "adaptive":
            bw = cv2.adaptiveThreshold(gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                35, 10)
                # 35x35 픽셀 범위를 기준으로, 작을수록 세밀-노이즈많음// 클수록 안정, 작은글자놓침
        else:
            # # 색상기준으로 100이하는 밝은색상으로 표시(50)
            # # 101 이상이면 검은색으로 표시
            bw = np.zeros_like(gray, dtype=np.uint8)

            bw[gray <= 120] = 50    # 글자색상 후보
            bw[gray > 120] = 0      # 밝은 배경 제거
        test_image_save(out_dir, "paragraphs", "2_binarize.png", bw, is_test)

        # 3) morphology: 글줄들은 "문단 덩어리"로 붙임
        kx = max(5, int(W * dilate_x_ratio))  # 가로방향으로 얼마나 붙일것인가
        print(" - kx: ", kx)
        ky = max(5, int(H * dilate_y_ratio))  # 세로 방향으로 얼마나 붙일것인가
        print(" - ky: ", ky)

        if kernel_mode == "min":
            kernel_px = min(kx, ky)
        elif kernel_mode == "max":
            kernel_px = max(kx, ky)
        else:
            kernel_px = (kx + ky)//2

        print(" - kernel_px: ", kernel_px)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_px, kernel_px))
        merged = cv2.dilate(bw, kernel, iterations=dilate_iter)
        test_image_save(out_dir, "paragraphs", "3_merged.png", merged, is_test)

        # 4) contour -> bounding boxex
        contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 초기 설정한 값을 기준으로 작은 크기 비율 계산
        img_area = float(H*W)
        min_area = img_area * min_area_ratio
        min_w = W * min_w_ratio
        min_h = H * min_h_ratio

        # 각 contour 들의 면적 계산
        boxes = []
        print("contours len: ", len(contours))

        if len(contours) == 0:
            raise ValueError("no contor detected in image...")

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h

            # 50X50px 은 ocr 안됨 무시 하도록
            if w < 50 or h < 50:
                print("이미지 크기 작음")
                continue

            # 너무 작지 않은 객체들의 x, y, w, h append
            boxes.append((x, y, w, h))
        print(" ")
        print("box count: ", str(boxes))

        if not boxes:
            print(f" - no paragraph blocks detected. try adjusting ratios(dilate_*_ratio, min_*_ratio).")
            return[]

        # 5) 정렬 (읽는 순서)
        if sort_mode == "reading":
            # 같은 줄 (비슷한 y)은 x로 정렬하기 위해 y tolerance를 둠
            y_tol = int(h*0.03) # 3% 높이 너는 같은 라인으로 간주
            boxes_sorted = sorted(boxes, key=lambda b: (b[1] // max(1, y_tol), b[0]))
        else:
            boxes_sorted = sorted(boxes, key=lambda b: (b[1] // b[0]))

        # 6) crop + save
        saved = []
        for i, (x, y, w, h) in enumerate(boxes_sorted, start=1):
            # pad = 8
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(W, x + w + pad)
            y2 = min(H, y + h + pad)

            crop = origin_img[y1:y2+1, x1:x2+1].copy()
            out_path = os.path.join(out_dir, f"{png_filename}_paragraph_{i:03d}.png")

            imwrite_unicode(out_path, crop)
            saved.append(out_path)

        return saved



    def preprocess_image(self, input_path:str, output_dir:str) -> list:

        # 스크립트 실행할때는 TRUE로, MAIN호출이면 FALSE로 실행
        if __name__ == "__main__":
            is_test = True
        else:
            is_test = False

        if not os.path.exists(input_path):
            print("[ERROR] 404 path not found")
            raise FileNotFoundError({"status": 404, "message": "path not found", "data":input_path})

        if os.path.isdir(input_path):
            print("[ERROR] 400 폴더 경로입니다. 이미지 파일 경로 필요.")
            raise IsADirectoryError({"status": 400, "message": "폴더 경로입니다. 이미지 파일 경로 필요.", "data":input_path})

        filename = input_path.split("\\")[-1]
        print("filename: ", filename)
        png_filename = filename.split(".")[0]

        # 배경 제거 관련 이미지
        output_dir_product = os.path.join(output_dir, png_filename)
        os.makedirs(output_dir_product, exist_ok=True)
        print("output_dir_product: ", output_dir_product)

        ## 1. ★ 검은색 배경이 있는 jpg이미지에서 박스만 추출
        try:
            cropped, origin_cropped = self.black_background_trim(input_path, output_dir_product, png_filename, is_test)
        except Exception as e:
            print(f"[ERROR] 500 background trim failed: {e}")
            return {"status": 500, "message": f"background trim failed: {e}"}

        # 2. ★ 배경 잘라낸 png 이미지에서 문단 별 잘라내기
        try:
            saved_files = self.crop_paragraphs(
                img = cropped,
                origin_img = origin_cropped,
                out_dir = output_dir_product,

                # -- binarization --
                binarize_mode= "otsu", # otsu or adaptive
                png_filename = png_filename,

                # -- morphology ( 문단 덩어리로 붙이기 ) --
                # 문단내 줄들이 잘 붙어있으면 ▼
                # 줄 간 간격이 작으면 ▼
                dilate_x_ratio= 0.02,   # 이미지 너비 대비 가로 커널 비율
                dilate_y_ratio= 0.02,   # 이미지 너비 대비 세로 커널 비율
                dilate_iter= 2,         # 원본은 2였음

                # -- filtering --
                # 숫자가 작으면 (작은 조각들도 추출)
                # 숫자가 크면 (큰 조각만 추출)
                min_area_ratio = 0.03,  # 전체 면적 대비 최소 문단 박스 비율
                min_w_ratio = 0.03,     # 0.15 이미지 너비 대비 최소 박스 너비 비율
                min_h_ratio = 0.03,     # 0.03 이미지 높이 대비 최소 박스 높이 비율

                # -- post --
                pad = 8,
                sort_mode = "reading",
                kernel_mode = "max",

                # -- test인 경우에는 단계별 이미지를 저장한다.
                is_test = is_test )

            print(f"{png_filename} saved: ")
            for p in saved_files:
                print(" - ", p)

        except ValueError as e:
            # 422 Unprocessable Entity 형식은 맞게 처리했으나 조건이 만족되지 못함
            print(f"[ERROR] 422 {e}")
            return {"status": 422, "message": f"{e}"}

        except Exception as e:
            print(f"[ERROR] 500 crop image failed: {e}")
            return {"status": 500, "message": f"crop image failed: {e}"}

        return saved_files

    if __name__ == "__main__":

        input_dir = r"N:\사용자폴더\전달파일\MX_BOX\file_3"
        output_dir = r"N:\사용자폴더\전달파일\MX_BOX\pdf_txt_rm"

        for filename in os.listdir(input_dir):
            print("-------- 실행 시작", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "--------")
            print("start filename:", filename)

            input_path = os.path.join(input_dir, filename)

            if not os.path.exists(input_path):
                print("[ERROR] 404 path not found")
                continue

            if os.path.isdir(input_path):
                print("[ERROR] 400 폴더 경로입니다. 이미지 파일 경로 필요.")
                continue

            doc_code = filename.split("_")[0]
            verification_id = filename.split("_")[1]

            result = main(input_path, output_dir, doc_code, verification_id)
            print(f"[{result}] | {filename}")

            print("-------- 실행 종료", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "--------")