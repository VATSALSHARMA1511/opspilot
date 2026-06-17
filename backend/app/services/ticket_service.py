from app.services.ai_service import classify_ticket
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.enums import TicketStatus, UserRole
from app.models.ticket import Ticket, TicketComment
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketCommentCreate

# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------
VALID_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.OPEN:        {TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS},
    TicketStatus.ASSIGNED:    {TicketStatus.IN_PROGRESS, TicketStatus.OPEN},
    TicketStatus.IN_PROGRESS: {TicketStatus.RESOLVED},
    TicketStatus.RESOLVED:    {TicketStatus.CLOSED, TicketStatus.IN_PROGRESS},
    TicketStatus.CLOSED:      set(),
}


def _write_audit(
    db: Session,
    user_id: int,
    action: str,
    entity_type: str,
    entity_id: int,
    old_value=None,
    new_value=None,
):
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(log)


# ---------------------------------------------------------------------------
# Ticket CRUD
# ---------------------------------------------------------------------------
def create_ticket(db: Session, data: TicketCreate, current_user: User) -> Ticket:
    ticket = Ticket(
        title=data.title,
        description=data.description,
        priority=data.priority,
        category=data.category,
        status=TicketStatus.OPEN,
        created_by_id=current_user.id,
        assigned_to_id=data.assigned_to_id,
    )
    db.add(ticket)
    db.flush()

    # AI classification — runs after flush so ticket has an ID, fails silently
    try:
        ai_result = classify_ticket(data.title, data.description)
        ticket.ai_category = ai_result.get("ai_category")
        ticket.ai_priority = ai_result.get("ai_priority")
        ticket.ai_summary = ai_result.get("ai_summary")
    except Exception:
        pass

    _write_audit(
        db, current_user.id, "CREATE", "ticket", ticket.id,
        new_value={"title": ticket.title, "status": ticket.status.value},
    )
    db.commit()
    db.refresh(ticket)
    return ticket


def get_tickets(
    db: Session,
    current_user: User,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    assigned_to: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Ticket], int]:
    page_size = min(page_size, 100)
    query = db.query(Ticket).filter(Ticket.deleted_at.is_(None))

    if status:
        query = query.filter(Ticket.status == TicketStatus(status))
    if priority:
        from app.models.enums import TicketPriority
        query = query.filter(Ticket.priority == TicketPriority(priority))
    if category:
        query = query.filter(Ticket.category == category)
    if assigned_to:
        query = query.filter(Ticket.assigned_to_id == assigned_to)

    total = query.count()
    items = query.order_by(Ticket.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_ticket(db: Session, ticket_id: int, current_user: User) -> Ticket:
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id,
        Ticket.deleted_at.is_(None),
    ).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


def update_ticket(db: Session, ticket_id: int, data: TicketUpdate, current_user: User) -> Ticket:
    ticket = get_ticket(db, ticket_id, current_user)
    if ticket.created_by_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only the creator or an admin can update this ticket")

    old_value = {
        "title": ticket.title,
        "description": ticket.description,
        "priority": ticket.priority.value if ticket.priority else None,
        "category": ticket.category,
    }

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ticket, field, value)
    ticket.updated_at = datetime.now(timezone.utc)

    _write_audit(db, current_user.id, "UPDATE", "ticket", ticket.id,
                 old_value=old_value, new_value=update_data)
    db.commit()
    db.refresh(ticket)
    return ticket


def change_status(db: Session, ticket_id: int, new_status: str, current_user: User) -> Ticket:
    ticket = get_ticket(db, ticket_id, current_user)
    old_status = ticket.status

    try:
        new_status_enum = TicketStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status value: {new_status}")

    allowed = VALID_TRANSITIONS.get(old_status, set())
    if not allowed:
        raise HTTPException(status_code=400, detail="Terminal state — no further transitions allowed")
    if new_status_enum not in allowed:
        allowed_values = [s.value for s in allowed]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition: {old_status.value} → {new_status}. Allowed: {allowed_values}",
        )
    if new_status_enum == TicketStatus.ASSIGNED and ticket.assigned_to_id is None:
        raise HTTPException(status_code=400, detail="Cannot set status to assigned without an assignee")

    ticket.status = new_status_enum
    ticket.updated_at = datetime.now(timezone.utc)
    if new_status_enum == TicketStatus.RESOLVED:
        ticket.resolved_at = datetime.now(timezone.utc)

    _write_audit(
        db, current_user.id, "STATUS_CHANGE", "ticket", ticket.id,
        old_value={"status": old_status.value},
        new_value={"status": new_status_enum.value},
    )
    db.commit()
    db.refresh(ticket)
    return ticket


def assign_ticket(db: Session, ticket_id: int, assignee_id: int, current_user: User) -> Ticket:
    ticket = get_ticket(db, ticket_id, current_user)
    assignee = db.query(User).filter(User.id == assignee_id, User.is_active.is_(True)).first()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee user not found")

    ticket.assigned_to_id = assignee_id
    ticket.updated_at = datetime.now(timezone.utc)
    db.flush()
    return change_status(db, ticket_id, TicketStatus.ASSIGNED.value, current_user)


def soft_delete_ticket(db: Session, ticket_id: int, current_user: User) -> None:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can delete tickets")
    ticket = get_ticket(db, ticket_id, current_user)
    ticket.deleted_at = datetime.now(timezone.utc)
    _write_audit(db, current_user.id, "DELETE", "ticket", ticket.id,
                 old_value={"status": ticket.status.value})
    db.commit()


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------
def add_comment(db: Session, ticket_id: int, data: TicketCommentCreate, current_user: User) -> TicketComment:
    get_ticket(db, ticket_id, current_user)  # 404 guard
    if data.is_internal and current_user.role not in (UserRole.ADMIN, UserRole.AGENT):
        raise HTTPException(status_code=403, detail="Only agents and admins can post internal comments")

    comment = TicketComment(
        ticket_id=ticket_id,
        author_id=current_user.id,
        body=data.body,
        is_internal=data.is_internal,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def get_comments(db: Session, ticket_id: int, current_user: User) -> list[TicketComment]:
    get_ticket(db, ticket_id, current_user)  # 404 guard
    query = db.query(TicketComment).filter(TicketComment.ticket_id == ticket_id)
    if current_user.role == UserRole.VIEWER:
        query = query.filter(TicketComment.is_internal.is_(False))
    return query.order_by(TicketComment.created_at.asc()).all()