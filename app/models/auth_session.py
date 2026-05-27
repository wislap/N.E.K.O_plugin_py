from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.core.database import Base
from app.core.time import utc_now


class RefreshTokenSession(Base):
    """Server-side refresh-token session for revocation and rotation."""

    __tablename__ = "refresh_token_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    jti = Column(String(64), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    issued_at = Column(DateTime, default=utc_now, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    replaced_by_jti = Column(String(64), nullable=True)
    client_id = Column(String(80), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class LoginAttempt(Base):
    """Coarse login throttling by submitted username/email identifier."""

    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String(255), unique=True, nullable=False, index=True)
    failed_count = Column(Integer, default=0, nullable=False)
    first_failed_at = Column(DateTime, nullable=True)
    last_failed_at = Column(DateTime, nullable=True)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
