from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class VersionBase(BaseModel):
    version: str = Field(..., min_length=1, max_length=20)
    changelog: Optional[str] = None
    download_url: Optional[str] = Field(None, max_length=500)
    min_app_version: Optional[str] = Field(None, max_length=20)
    max_app_version: Optional[str] = Field(None, max_length=20)


class VersionCreate(VersionBase):
    pass


class Version(VersionBase):
    id: int
    plugin_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
