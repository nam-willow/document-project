from pathlib import Path
from uuid import uuid4


def get_extension(filename: str) -> str:
    """
    파일 확장자를 소문자로 반환.
    """
    return Path(filename).suffix.lower()


def build_saved_filename(original_filename: str) -> str:
    """
    파일명 충돌 방지를 위해 UUID prefix 추가.
    """
    extension = Path(original_filename).suffix
    stem = Path(original_filename).stem
    return f"{uuid4().hex}_{stem}{extension}"