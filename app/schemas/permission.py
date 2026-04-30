"""
权限系统 Schema
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ========== Permission Schemas ==========

class PermissionBase(BaseModel):
    code: str
    name: str
    category: str
    description: Optional[str] = None


class PermissionCreate(PermissionBase):
    pass


class PermissionResponse(PermissionBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== Permission Group Schemas ==========

class PermissionGroupBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None


class PermissionGroupCreate(PermissionGroupBase):
    parent_id: Optional[int] = None
    permission_codes: Optional[List[str]] = []


class PermissionGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class PermissionGroupResponse(PermissionGroupBase):
    id: int
    parent_id: Optional[int]
    is_active: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime
    permissions: List[PermissionResponse] = []

    class Config:
        from_attributes = True


# ========== User Permission Schemas ==========

class PermissionAssignRequest(BaseModel):
    group_ids: List[int]


class UserPermissionsResponse(BaseModel):
    user_id: int
    username: str
    is_admin: bool
    permissions: List[str]
    groups: List[str]


# ========== Audit Log Schemas ==========

class PermissionAuditLogResponse(BaseModel):
    id: int
    action: str
    target_type: str
    target_id: int
    operator_id: int
    details: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
