from datetime import datetime
from pydantic import AliasPath, BaseModel, ConfigDict, Field
from app.models.enums import ManagerAction, TicketPriority, TicketStatus
from app.schemas.user import DepartmentResponse, UserResponse


class TicketCreate(BaseModel):
    title: str = Field(max_length=255)
    description: str
    priority: TicketPriority = TicketPriority.MEDIUM
    category: str | None = Field(default=None, max_length=100)
    target_department_id: int


class TicketUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    priority: TicketPriority | None = None
    category: str | None = Field(default=None, max_length=100)
    resolution_notes: str | None = None


class TicketReviewBody(BaseModel):
    action: ManagerAction  # accepted or rejected
    rejection_reason: str | None = None


class TicketAssignBody(BaseModel):
    assignee_id: int


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category: str | None
    created_by: UserResponse = Field(validation_alias=AliasPath("creator"))
    target_department: DepartmentResponse
    assigned_to: UserResponse | None = Field(
        default=None, validation_alias=AliasPath("assignee")
    )
    reviewing_manager: UserResponse | None = None
    manager_action: ManagerAction
    rejection_reason: str | None
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


class TicketCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    author_id: int
    author_name: str = Field(validation_alias=AliasPath("author", "full_name"))
    body: str
    is_internal: bool
    created_at: datetime