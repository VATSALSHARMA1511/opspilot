from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.ticket import Ticket, TicketComment
    from app.models.audit_log import AuditLog


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    department: Mapped["Department | None"] = relationship(back_populates="users")
    created_tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="creator",
        foreign_keys="Ticket.created_by_id",
    )
    assigned_tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="assignee",
        foreign_keys="Ticket.assigned_to_id",
    )
    managed_tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="reviewing_manager",
        foreign_keys="Ticket.manager_id",
    )
    comments: Mapped[list["TicketComment"]] = relationship(back_populates="author")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")