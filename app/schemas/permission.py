"""
权限系统 Schema
"""
from pydantic import BaseModel, ConfigDict, Field
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
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ========== Permission Group Schemas ==========

class PermissionGroupBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    level: int = Field(10, ge=0, le=999)


class PermissionGroupCreate(PermissionGroupBase):
    parent_id: Optional[int] = None
    permission_codes: List[str] = Field(default_factory=list)


class PermissionGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    level: Optional[int] = Field(None, ge=0, le=999)
    permission_codes: Optional[List[str]] = None


class PermissionGroupResponse(PermissionGroupBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: Optional[int]
    group_type: Optional[str] = None
    is_active: bool
    is_system: bool
    user_count: int = 0
    created_at: datetime
    updated_at: datetime
    permissions: List[PermissionResponse] = []


# ========== User Permission Schemas ==========

class PermissionAssignRequest(BaseModel):
    group_ids: List[int]


class UserPermissionsResponse(BaseModel):
    user_id: int
    username: str
    is_admin: bool
    is_super_admin: bool = False
    level: int = 0
    permissions: List[str]
    groups: List[str]
    roles: List[PermissionGroupResponse] = Field(default_factory=list)


# ========== Audit Log Schemas ==========

class PermissionAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    target_type: str
    target_id: int
    operator_id: int
    details: Optional[str]
    created_at: datetime
