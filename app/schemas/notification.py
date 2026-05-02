from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class Notification(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    type: str
    title: str
    content: Optional[str] = None
    target_url: Optional[str] = None
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None
