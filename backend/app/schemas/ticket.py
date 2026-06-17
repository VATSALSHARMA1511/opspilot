from datetime import datetime

from pydantic import AliasPath, BaseModel, ConfigDict, Field

from app.models.enums import TicketPriority, TicketStatus
from app.schemas.user import UserResponse


class TicketCreate(BaseModel):
    title: str = Field(max_length=255)
    description: str
    priority: TicketPriority = TicketPriority.MEDIUM
    category: str | None = Field(default=None, max_length=100)
    assigned_to_id: int | None = None


class TicketUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    category: str | None = Field(default=None, max_length=100)
    assigned_to_id: int | None = None
    resolution_notes: str | None = None
    resolved_at: datetime | None = None


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category: str | None
    created_by: UserResponse = Field(validation_alias=AliasPath("creator"))
    assigned_to: UserResponse | None = Field(
        default=None, validation_alias=AliasPath("assignee")
    )
    resolution_notes: str | None
    ai_category: str | None = None
    ai_priority: str | None = None
    ai_summary: str | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    deleted_at: datetime | None


class TicketCommentCreate(BaseModel):
    body: str
    is_internal: bool = False


class TicketCommentUpdate(BaseModel):
    body: str | None = None
    is_internal: bool | None = None


class TicketCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    author_id: int
    author_name: str = Field(validation_alias=AliasPath("author", "full_name"))
    body: str
    is_internal: bool
    created_at: datetime


class TicketEmbeddingCreate(BaseModel):
    ticket_id: int
    embedding: list[float] = Field(min_length=1536, max_length=1536)


class TicketEmbeddingUpdate(BaseModel):
    embedding: list[float] | None = Field(default=None, min_length=1536, max_length=1536)


class TicketEmbeddingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    embedding: list[float]
    created_at: datetime
