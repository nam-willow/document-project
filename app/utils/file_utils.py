from pathlib import Path
from uuid import uuid4
import cv2
import numpy as np
import os

def get_extension(filename: str) -> str:
    """
    파일 확장자를 소문자로 반환.
    """
    return Path(filename).suffix.lower()


def build_saved_filename(original_filename: str) -> str:
    """
    파일명 충돌 방지를 위해 UUID prefix 추가.
    """
    print("build_saved_filename called | original_filename=%s", original_filename)
    extension = Path(original_filename).suffix
    stem = Path(original_filename).stem
    return f"{uuid4().hex}_{stem}{extension}"

def imread_unicode(path: str) : 
    """
    유니코드 경로에서도 OpenCV로 이미지 읽기.
    """
    try:
        data = np.fromfile(path, dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    except ValueError as e:
        return f"image read error: {e}"

    return img

def imwrite_unicode(path: str, img):
    """
    유니코드 경로에서도 OpenCV로 이미지 쓰기.
    """
    try:
        ext = get_extension(path)
        success, encoded = cv2.imencode(ext, img)
    except ValueError as e:
        print(f"image write error: {e}")
        return (f"image write error: {e}")
    encoded.tofile(path)

def test_image_save(out_dir, foldername, filename, img, is_test):
    """
    test 모드냐에 따라서 이미지 저장 여부 결정하는 함수
    """
    if is_test == True : 
        outpath = os.path.join(out_dir, foldername)
        os.makedirs(outpath, exist_ok=True)
        out_path = os.path.join(outpath, filename)
        imwrite_unicode(str(out_path), img)