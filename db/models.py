from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint


class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email"),
        UniqueConstraint("name"),
    )

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, nullable=False, max_length=120)
    email: str = Field(index=True, nullable=False, max_length=255)
    hashed_password: str = Field(nullable=False, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class PasswordRequest(SQLModel, table=True):
    __tablename__ = "password_requests"

    id: int | None = Field(default=None, primary_key=True)
    user_name: str = Field(nullable=False, max_length=120)
    email: str = Field(nullable=False, max_length=255)
    hashed_new_password: str = Field(nullable=False, max_length=255)
    status: str = Field(default="pendente", nullable=False, max_length=32)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class RegistrationRequest(SQLModel, table=True):
    __tablename__ = "registration_requests"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, max_length=120)
    email: str = Field(nullable=False, max_length=255)
    hashed_password: str = Field(nullable=False, max_length=255)
    status: str = Field(default="pendente", nullable=False, max_length=32)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class PopRequest(SQLModel, table=True):
    __tablename__ = "pop_requests"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(nullable=False, max_length=255)
    description: str = Field(nullable=False, max_length=2000)
    file_name: str = Field(nullable=False, max_length=255)
    file_path: str = Field(nullable=False, max_length=1024)
    status: str = Field(default="pendente", nullable=False, max_length=32)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
