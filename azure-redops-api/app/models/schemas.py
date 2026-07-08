from pydantic import BaseModel
from typing import Optional, Dict, Any

class ActivityRequest(BaseModel):
    activity: str
    token_name: Optional[str] = None
    flags: Optional[Dict[str, Any]] = None

class TokenSaveRequest(BaseModel):
    name: str
    token_data: dict

class PhishStartRequest(BaseModel):
    tenant_id: Optional[str] = None