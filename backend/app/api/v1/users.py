from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.department import Department
from app.models.enums import UserRole
from app.schemas.user import DepartmentResponse, UserResponse

router = APIRouter(tags=["users"])


@router.get("/users", response_model=list[UserResponse])
def list_users(
    department_id: Optional[int] = Query(None),
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(User).filter(User.is_active.is_(True))

    # Managers can only list users in their own department
    if current_user.role == UserRole.MANAGER:
        query = query.filter(User.department_id == current_user.department_id)
    elif department_id:
        query = query.filter(User.department_id == department_id)

    if role:
        query = query.filter(User.role == UserRole(role))

    return query.order_by(User.full_name).all()


@router.get("/departments", response_model=list[DepartmentResponse])
def list_departments(
    db: Session = Depends(get_db),
):
    return db.query(Department).order_by(Department.name).all()