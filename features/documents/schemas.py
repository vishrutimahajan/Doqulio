from pydantic import BaseModel
from typing import Optional

class DocumentResponse(BaseModel):
    id: str
    filename: str
    owner_uid: str
    url: Optional[str] = None
