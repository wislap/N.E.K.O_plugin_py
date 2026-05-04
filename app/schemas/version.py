from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime

SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"
VERIFICATION_STATUS_PATTERN = r"^(unverified|pending|passed|failed)$"


class VersionBase(BaseModel):
    version: str = Field(..., min_length=1, max_length=20)
    changelog: Optional[str] = None
    download_url: Optional[str] = Field(None, max_length=500)
    min_app_version: Optional[str] = Field(None, max_length=20)
    max_app_version: Optional[str] = Field(None, max_length=20)

    # Trusted release provenance. These fields are optional so older clients can
    # keep creating plain versions while newer clients submit CI/package proof.
    source_repo_url: Optional[str] = Field(None, max_length=500)
    source_commit: Optional[str] = Field(None, max_length=64)
    release_tag: Optional[str] = Field(None, max_length=100)
    release_url: Optional[str] = Field(None, max_length=500)
    actions_run_url: Optional[str] = Field(None, max_length=500)
    package_url: Optional[str] = Field(None, max_length=500)
    package_sha256: Optional[str] = Field(None, pattern=SHA256_PATTERN)
    payload_hash: Optional[str] = Field(None, pattern=SHA256_PATTERN)
    neko_repo: Optional[str] = Field(None, max_length=200)
    neko_ref: Optional[str] = Field(None, max_length=100)
    neko_commit: Optional[str] = Field(None, max_length=64)
    verification_status: str = Field("unverified", pattern=VERIFICATION_STATUS_PATTERN)
    verification_summary: Optional[str] = None


class VersionCreate(VersionBase):
    pass


class Version(VersionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plugin_id: int
    created_at: datetime
