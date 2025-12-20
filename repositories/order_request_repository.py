from __future__ import annotations

from typing import List, Optional

from sqlmodel import Session, select

from db.order_models import OrderRequest


def create_request(session: Session, origin: str, description: str, total_orders: int | None = None) -> OrderRequest:
    request = OrderRequest(
        origin=origin.strip(),
        description=description.strip(),
        total_orders=total_orders,
    )
    session.add(request)
    session.commit()
    session.refresh(request)
    return request


def list_pending(session: Session) -> List[OrderRequest]:
    stmt = select(OrderRequest).where(OrderRequest.status == "pendente").order_by(OrderRequest.created_at.desc())
    return list(session.exec(stmt).all())


def list_approved(session: Session) -> List[OrderRequest]:
    stmt = select(OrderRequest).where(OrderRequest.status == "aprovado").order_by(OrderRequest.created_at.desc())
    return list(session.exec(stmt).all())


def get_by_id(session: Session, request_id: int) -> Optional[OrderRequest]:
    return session.get(OrderRequest, request_id)


def update_status(session: Session, request: OrderRequest, status: str) -> OrderRequest:
    request.status = status
    session.add(request)
    session.commit()
    session.refresh(request)
    return request


def delete_by_id(session: Session, request_id: int) -> bool:
    req = session.get(OrderRequest, request_id)
    if req is None:
        return False
    session.delete(req)
    session.commit()
    return True
