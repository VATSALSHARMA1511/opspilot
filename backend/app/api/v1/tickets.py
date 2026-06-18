from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

class TicketStatusBody(BaseModel):
    status: str
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.pagination import PaginatedResponse
from app.schemas.ticket import (
    TicketAssignBody,
    TicketCommentCreate,
    TicketCommentResponse,
    TicketCreate,
    TicketResponse,
    TicketReviewBody,
    TicketUpdate,
)
from app.services import ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketResponse, status_code=201)
def create_ticket(
    data: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ticket_service.create_ticket(db, data, current_user)


@router.get("", response_model=PaginatedResponse[TicketResponse])
def list_tickets(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    assigned_to: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = ticket_service.get_tickets(
        db, current_user, status, priority, category, assigned_to, page, page_size
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ticket_service.get_ticket(db, ticket_id, current_user)


@router.put("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ticket_service.update_ticket(db, ticket_id, data, current_user)


@router.patch("/{ticket_id}/review", response_model=TicketResponse)
def review_ticket(
    ticket_id: int,
    body: TicketReviewBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ticket_service.review_ticket(
        db, ticket_id, body.action, body.rejection_reason, current_user
    )


@router.patch("/{ticket_id}/assign", response_model=TicketResponse)
def assign_ticket(
    ticket_id: int,
    body: TicketAssignBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ticket_service.assign_ticket(db, ticket_id, body.assignee_id, current_user)


@router.patch("/{ticket_id}/status", response_model=TicketResponse)
def change_status(
    ticket_id: int,
    body: TicketStatusBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ticket_service.change_status(db, ticket_id, body.status, current_user)


@router.delete("/{ticket_id}", status_code=204)
def delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket_service.soft_delete_ticket(db, ticket_id, current_user)


@router.post("/{ticket_id}/comments", response_model=TicketCommentResponse, status_code=201)
def add_comment(
    ticket_id: int,
    data: TicketCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ticket_service.add_comment(db, ticket_id, data, current_user)


@router.get("/{ticket_id}/comments", response_model=list[TicketCommentResponse])
def get_comments(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ticket_service.get_comments(db, ticket_id, current_user)