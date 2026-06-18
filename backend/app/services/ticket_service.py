from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.enums import ManagerAction, TicketStatus, TicketPriority, UserRole
from app.models.ticket import Ticket, TicketComment
from app.models.user import User
from app.models.department import Department
from app.models.audit_log import AuditLog
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketCommentCreate
from app.services.ai_service import classify_ticket

# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------
VALID_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.PENDING_REVIEW: set(),
    TicketStatus.ACCEPTED:       set(),
    TicketStatus.ASSIGNED:       {TicketStatus.IN_PROGRESS},
    TicketStatus.IN_PROGRESS:    {TicketStatus.RESOLVED},
    TicketStatus.RESOLVED:       {TicketStatus.CLOSED},
    TicketStatus.REJECTED:       set(),
    TicketStatus.CLOSED:         set(),
}


def _write_audit(db, user_id, action, entity_type, entity_id, old_value=None, new_value=None):
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


def _get_ticket_or_404(db: Session, ticket_id: int) -> Ticket:
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id,
        Ticket.deleted_at.is_(None),
    ).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


def _can_view_ticket(ticket: Ticket, current_user: User) -> bool:
    if current_user.role == UserRole.ADMIN:
        return True
    if current_user.role == UserRole.MANAGER:
        return ticket.target_department_id == current_user.department_id
    if current_user.role == UserRole.MEMBER:
        return ticket.assigned_to_id == current_user.id
    # any logged-in user can see tickets they created
    return ticket.created_by_id == current_user.id


# ---------------------------------------------------------------------------
# Ticket CRUD
# ---------------------------------------------------------------------------
def create_ticket(db: Session, data: TicketCreate, current_user: User) -> Ticket:
    dept = db.query(Department).filter(Department.id == data.target_department_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Target department not found")

    ticket = Ticket(
        title=data.title,
        description=data.description,
        priority=data.priority,
        category=data.category,
        status=TicketStatus.PENDING_REVIEW,
        manager_action=ManagerAction.PENDING,
        created_by_id=current_user.id,
        target_department_id=data.target_department_id,
    )
    db.add(ticket)
    db.flush()

    try:
        ai_result = classify_ticket(data.title, data.description)
        ticket.ai_category = ai_result.get("ai_category")
        ticket.ai_priority = ai_result.get("ai_priority")
        ticket.ai_summary = ai_result.get("ai_summary")
    except Exception:
        pass

    _write_audit(db, current_user.id, "CREATE", "ticket", ticket.id,
                 new_value={"title": ticket.title, "status": ticket.status.value})
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

    # Role-based visibility
    if current_user.role == UserRole.ADMIN:
        pass  # sees everything
    elif current_user.role == UserRole.MANAGER:
        query = query.filter(Ticket.target_department_id == current_user.department_id)
    elif current_user.role == UserRole.MEMBER:
        # sees assigned tickets + tickets they created
        query = query.filter(
            (Ticket.assigned_to_id == current_user.id) |
            (Ticket.created_by_id == current_user.id)
        )
    else:
        # fallback — only own tickets
        query = query.filter(Ticket.created_by_id == current_user.id)

    if status:
        query = query.filter(Ticket.status == TicketStatus(status))
    if priority:
        query = query.filter(Ticket.priority == TicketPriority(priority))
    if category:
        query = query.filter(Ticket.category == category)
    if assigned_to:
        query = query.filter(Ticket.assigned_to_id == assigned_to)

    total = query.count()
    items = (query.order_by(Ticket.created_at.desc())
             .offset((page - 1) * page_size)
             .limit(page_size)
             .all())
    return items, total


def get_ticket(db: Session, ticket_id: int, current_user: User) -> Ticket:
    ticket = _get_ticket_or_404(db, ticket_id)
    if not _can_view_ticket(ticket, current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    return ticket


def update_ticket(db: Session, ticket_id: int, data: TicketUpdate, current_user: User) -> Ticket:
    ticket = get_ticket(db, ticket_id, current_user)

    # Only creator can edit, only while pending review
    if ticket.created_by_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only the creator can edit this ticket")
    if ticket.status != TicketStatus.PENDING_REVIEW and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Ticket can only be edited while pending review")

    old_value = {"title": ticket.title, "description": ticket.description}
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ticket, field, value)
    ticket.updated_at = datetime.now(timezone.utc)

    _write_audit(db, current_user.id, "UPDATE", "ticket", ticket.id,
                 old_value=old_value, new_value=update_data)
    db.commit()
    db.refresh(ticket)
    return ticket


def review_ticket(db: Session, ticket_id: int, action: ManagerAction,
                  rejection_reason: Optional[str], current_user: User) -> Ticket:
    ticket = _get_ticket_or_404(db, ticket_id)

    if current_user.role not in (UserRole.MANAGER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only managers can review tickets")
    if current_user.role == UserRole.MANAGER and ticket.target_department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="You can only review tickets for your department")
    if ticket.status != TicketStatus.PENDING_REVIEW:
        raise HTTPException(status_code=400, detail="Only pending_review tickets can be reviewed")

    if action == ManagerAction.ACCEPTED:
        ticket.status = TicketStatus.ACCEPTED
        ticket.manager_action = ManagerAction.ACCEPTED
    elif action == ManagerAction.REJECTED:
        if not rejection_reason:
            raise HTTPException(status_code=400, detail="rejection_reason required when rejecting")
        ticket.status = TicketStatus.REJECTED
        ticket.manager_action = ManagerAction.REJECTED
        ticket.rejection_reason = rejection_reason
    else:
        raise HTTPException(status_code=400, detail="action must be accepted or rejected")

    ticket.manager_id = current_user.id
    ticket.updated_at = datetime.now(timezone.utc)

    _write_audit(db, current_user.id, "REVIEW", "ticket", ticket.id,
                 new_value={"action": action.value})
    db.commit()
    db.refresh(ticket)
    return ticket


def assign_ticket(db: Session, ticket_id: int, assignee_id: int, current_user: User) -> Ticket:
    ticket = _get_ticket_or_404(db, ticket_id)

    if current_user.role not in (UserRole.MANAGER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only managers can assign tickets")
    if current_user.role == UserRole.MANAGER and ticket.target_department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="You can only assign tickets in your department")
    if ticket.status != TicketStatus.ACCEPTED:
        raise HTTPException(status_code=400, detail="Ticket must be accepted before assignment")

    assignee = db.query(User).filter(
        User.id == assignee_id,
        User.is_active.is_(True),
        User.department_id == ticket.target_department_id,
    ).first()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found in target department")
    if assignee.role not in (UserRole.MEMBER, UserRole.MANAGER):
        raise HTTPException(status_code=400, detail="Can only assign to members or managers")

    ticket.assigned_to_id = assignee_id
    ticket.status = TicketStatus.ASSIGNED
    ticket.updated_at = datetime.now(timezone.utc)

    _write_audit(db, current_user.id, "ASSIGN", "ticket", ticket.id,
                 new_value={"assigned_to_id": assignee_id})
    db.commit()
    db.refresh(ticket)
    return ticket


def change_status(db: Session, ticket_id: int, new_status: str, current_user: User) -> Ticket:
    ticket = get_ticket(db, ticket_id, current_user)

    try:
        new_status_enum = TicketStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")

    # Only assigned member or manager of dept or admin can change status
    if current_user.role == UserRole.MEMBER and ticket.assigned_to_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only update status on your assigned tickets")
    if current_user.role == UserRole.MANAGER and ticket.target_department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Access denied")

    allowed = VALID_TRANSITIONS.get(ticket.status, set())
    if not allowed:
        raise HTTPException(status_code=400, detail="No further transitions allowed from this status")
    if new_status_enum not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition: {ticket.status.value} → {new_status}. Allowed: {[s.value for s in allowed]}",
        )

    old_status = ticket.status
    ticket.status = new_status_enum
    ticket.updated_at = datetime.now(timezone.utc)
    if new_status_enum == TicketStatus.RESOLVED:
        ticket.resolved_at = datetime.now(timezone.utc)

    _write_audit(db, current_user.id, "STATUS_CHANGE", "ticket", ticket.id,
                 old_value={"status": old_status.value},
                 new_value={"status": new_status_enum.value})
    db.commit()
    db.refresh(ticket)
    return ticket


def soft_delete_ticket(db: Session, ticket_id: int, current_user: User) -> None:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can delete tickets")
    ticket = _get_ticket_or_404(db, ticket_id)
    ticket.deleted_at = datetime.now(timezone.utc)
    _write_audit(db, current_user.id, "DELETE", "ticket", ticket.id,
                 old_value={"status": ticket.status.value})
    db.commit()


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------
def add_comment(db: Session, ticket_id: int, data: TicketCommentCreate, current_user: User) -> TicketComment:
    ticket = get_ticket(db, ticket_id, current_user)

    if data.is_internal and current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(status_code=403, detail="Only managers and admins can post internal comments")

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
    ticket = get_ticket(db, ticket_id, current_user)
    query = db.query(TicketComment).filter(TicketComment.ticket_id == ticket_id)
    if current_user.role == UserRole.MEMBER and ticket.assigned_to_id != current_user.id:
        query = query.filter(TicketComment.is_internal.is_(False))
    return query.order_by(TicketComment.created_at.asc()).all()