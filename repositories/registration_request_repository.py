from __future__ import annotations

from typing import List, Optional

from sqlmodel import Session, select

from db.models import RegistrationRequest


def create_request(session: Session, name: str, email: str, hashed_password: str) -> RegistrationRequest:
    request = RegistrationRequest(
        name=name.strip(),
        email=email.strip().lower(),
        hashed_password=hashed_password,
    )
    session.add(request)
    session.commit()
    session.refresh(request)
    return request


def list_pending(session: Session) -> List[RegistrationRequest]:
    statement = select(RegistrationRequest).where(RegistrationRequest.status == "pendente").order_by(RegistrationRequest.created_at.desc())
    return list(session.exec(statement).all())


def get_by_id(session: Session, request_id: int) -> Optional[RegistrationRequest]:
    return session.get(RegistrationRequest, request_id)


def update_status(session: Session, request: RegistrationRequest, status: str) -> RegistrationRequest:
    request.status = status
    session.add(request)
    session.commit()
    session.refresh(request)
    return request
