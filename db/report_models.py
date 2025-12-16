from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class ReportRequest(SQLModel, table=True):
    __tablename__ = "report_requests"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(nullable=False, max_length=255)
    description: str = Field(nullable=False, max_length=2000)
    file_name: str = Field(nullable=False, max_length=255)
    file_path: str = Field(nullable=False, max_length=1024)
    status: str = Field(default="pendente", nullable=False, max_length=32)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
