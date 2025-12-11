from __future__ import annotations

from typing import List, Optional

from sqlmodel import Session, select

from db.models import PopRequest


def create_request(session: Session, title: str, description: str, file_name: str, file_path: str) -> PopRequest:
    request = PopRequest(
        title=title.strip(),
        description=description.strip(),
        file_name=file_name.strip(),
        file_path=file_path.strip(),
    )
    session.add(request)
    session.commit()
    session.refresh(request)
    return request


def list_pending(session: Session) -> List[PopRequest]:
    statement = select(PopRequest).where(PopRequest.status == "pendente").order_by(PopRequest.created_at.desc())
    return list(session.exec(statement).all())


def list_approved(session: Session) -> List[PopRequest]:
    statement = select(PopRequest).where(PopRequest.status == "aprovado").order_by(PopRequest.created_at.desc())
    return list(session.exec(statement).all())


def get_by_id(session: Session, request_id: int) -> Optional[PopRequest]:
    return session.get(PopRequest, request_id)


def update_status(session: Session, request: PopRequest, status: str) -> PopRequest:
    request.status = status
    session.add(request)
    session.commit()
    session.refresh(request)
    return request


def delete_by_id(session: Session, request_id: int) -> bool:
    req = session.get(PopRequest, request_id)
    if req is None:
        return False
    session.delete(req)
    session.commit()
    return True
