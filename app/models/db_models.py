from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any


@dataclass
class DocumentRecord:
    """
    실제 ORM(SQLAlchemy)로 바꾸기 전의 임시 DB 모델.
    """
    filename: str
    file_type: str
    saved_path: str
    extracted_json: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)