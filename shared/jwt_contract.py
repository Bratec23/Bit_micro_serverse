from pydantic import BaseModel
from typing import Optional


class JWTPayload(BaseModel):
    user_id: int
    email: str
    role: str
    department_id: Optional[int] = None
    full_name: str = ""