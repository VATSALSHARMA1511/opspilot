from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ManagerAction, TicketPriority, TicketStatus

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.user import User


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_created_by_id", "created_by_id"),
        Index("ix_tickets_assigned_to_id", "assigned_to_id"),
        Index("ix_tickets_target_department_id", "target_department_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TicketStatus.PENDING_REVIEW,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, name="ticket_priority", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TicketPriority.MEDIUM,
    )
    category: Mapped[str | None] = mapped_column(String(100))

    # Who created it
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Which department it's routed to
    target_department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Which manager reviewed it
    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Manager decision
    manager_action: Mapped[ManagerAction] = mapped_column(
        Enum(ManagerAction, name="manager_action", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ManagerAction.PENDING,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    # Assigned member
    assigned_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    resolution_notes: Mapped[str | None] = mapped_column(Text)
    ai_category: Mapped[str | None] = mapped_column(String(100))
    ai_priority: Mapped[str | None] = mapped_column(String(50))
    ai_summary: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    creator: Mapped["User"] = relationship(
        back_populates="created_tickets",
        foreign_keys=[created_by_id],
    )
    target_department: Mapped["Department"] = relationship(
        back_populates="tickets",
        foreign_keys=[target_department_id],
    )
    reviewing_manager: Mapped["User | None"] = relationship(
        back_populates="managed_tickets",
        foreign_keys=[manager_id],
    )
    assignee: Mapped["User | None"] = relationship(
        back_populates="assigned_tickets",
        foreign_keys=[assigned_to_id],
    )
    comments: Mapped[list["TicketComment"]] = relationship(
        back_populates="ticket",
        cascade="save-update, merge",
    )
    embedding: Mapped["TicketEmbedding | None"] = relationship(
        back_populates="ticket",
        uselist=False,
        cascade="save-update, merge",
    )


class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ticket: Mapped["Ticket"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship(back_populates="comments")


class TicketEmbedding(Base):
    __tablename__ = "ticket_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ticket: Mapped["Ticket"] = relationship(back_populates="embedding")