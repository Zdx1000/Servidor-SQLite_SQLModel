from __future__ import annotations

from typing import List, Optional

from sqlmodel import Session, select

from db.report_models import ReportRequest


def create_request(session: Session, title: str, description: str, file_name: str, file_path: str) -> ReportRequest:
    request = ReportRequest(
        title=title.strip(),
        description=description.strip(),
        file_name=file_name.strip(),
        file_path=file_path.strip(),
    )
    session.add(request)
    session.commit()
    session.refresh(request)
    return request


def list_pending(session: Session) -> List[ReportRequest]:
    statement = select(ReportRequest).where(ReportRequest.status == "pendente").order_by(ReportRequest.created_at.desc())
    return list(session.exec(statement).all())


def list_approved(session: Session) -> List[ReportRequest]:
    statement = select(ReportRequest).where(ReportRequest.status == "aprovado").order_by(ReportRequest.created_at.desc())
    return list(session.exec(statement).all())


def get_by_id(session: Session, request_id: int) -> Optional[ReportRequest]:
    return session.get(ReportRequest, request_id)


def update_status(session: Session, request: ReportRequest, status: str) -> ReportRequest:
    request.status = status
    session.add(request)
    session.commit()
    session.refresh(request)
    return request


def delete_by_id(session: Session, request_id: int) -> bool:
    req = session.get(ReportRequest, request_id)
    if req is None:
        return False
    session.delete(req)
    session.commit()
    return True
