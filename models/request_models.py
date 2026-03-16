from pydantic import BaseModel, Field


class SaveModeRequest(BaseModel):
    """
    나중에 JSON 응답만 할지, DB까지 저장할지 선택할 때 사용할 입력 모델 예시.
    """
    save_to_db: bool = Field(default=False, description="DB 저장 여부")