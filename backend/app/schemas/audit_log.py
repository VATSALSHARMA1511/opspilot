from datetime import datetime
from typing import Any

from pydantic import AliasPath, BaseModel, ConfigDict, Field

from app.schemas.user import UserResponse


class AuditLogCreate(BaseModel):
    user_id: int | None = None
    action: str = Field(max_length=100)
    entity_type: str = Field(max_length=100)
    entity_id: int
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None


class AuditLogUpdate(BaseModel):
    user_id: int | None = None
    action: str | None = Field(default=None, max_length=100)
    entity_type: str | None = Field(default=None, max_length=100)
    entity_id: int | None = None
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user: UserResponse | None = Field(default=None, validation_alias=AliasPath("user"))
    action: str
    entity_type: str
    entity_id: int
    old_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    timestamp: datetime
