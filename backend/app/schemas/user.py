from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from app.models.enums import UserRole


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: UserRole = UserRole.MEMBER
    department_id: int | None = None
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)
    full_name: str | None = None
    role: UserRole | None = None
    department_id: int | None = None
    is_active: bool | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.lower()


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    department: DepartmentResponse | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime