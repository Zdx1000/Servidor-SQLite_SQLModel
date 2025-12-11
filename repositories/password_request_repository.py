from __future__ import annotations

from typing import List, Optional

from sqlmodel import Session, select

from db.models import PasswordRequest


def create_request(session: Session, user_name: str, email: str, hashed_new_password: str) -> PasswordRequest:
    request = PasswordRequest(
        user_name=user_name.strip(),
        email=email.strip().lower(),
        hashed_new_password=hashed_new_password,
    )
    session.add(request)
    session.commit()
    session.refresh(request)
    return request


def list_pending(session: Session) -> List[PasswordRequest]:
    statement = select(PasswordRequest).where(PasswordRequest.status == "pendente").order_by(PasswordRequest.created_at.desc())
    return list(session.exec(statement).all())


def get_by_id(session: Session, request_id: int) -> Optional[PasswordRequest]:
    return session.get(PasswordRequest, request_id)


def update_status(session: Session, request: PasswordRequest, status: str) -> PasswordRequest:
    request.status = status
    session.add(request)
    session.commit()
    session.refresh(request)
    return request
