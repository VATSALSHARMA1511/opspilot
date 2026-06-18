import hashlib

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from redis import Redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_db, get_redis, get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    decode_token,
)
from app.models.user import User
from app.schemas.user import UserCreate

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register")
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
):
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    
    db_user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role,
        department_id=user_in.department_id,
        is_active=user_in.is_active,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    access_token = create_access_token({"sub": db_user.email})
    refresh_token = create_refresh_token({"sub": db_user.email})
    
    refresh_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
    redis_client.setex(
        f"refresh:{db_user.id}",
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        refresh_hash,
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "full_name": db_user.full_name,
            "email": db_user.email,
            "role": db_user.role,
            "department_id": db_user.department_id,
        },
    }


@router.post("/login")
def login(
    login_in: LoginRequest,
    db: Session = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
):
    user = db.query(User).filter(User.email == login_in.email.lower()).first()
    if not user or not verify_password(login_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
        )
    
    access_token = create_access_token({"sub": user.email})
    refresh_token = create_refresh_token({"sub": user.email})
    
    refresh_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
    redis_client.setex(
        f"refresh:{user.id}",
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        refresh_hash,
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "department_id": user.department_id,
        },
    }


@router.post("/refresh")
def refresh(
    refresh_in: RefreshRequest,
    db: Session = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
):
    payload = decode_token(refresh_in.refresh_token)
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
        )
    
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    refresh_hash = hashlib.sha256(refresh_in.refresh_token.encode("utf-8")).hexdigest()
    stored_hash = redis_client.get(f"refresh:{user.id}")
    if not stored_hash or stored_hash != refresh_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    access_token = create_access_token({"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    current_user: User = Depends(get_current_user),
    redis_client: Redis = Depends(get_redis),
):
    redis_client.delete(f"refresh:{current_user.id}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
