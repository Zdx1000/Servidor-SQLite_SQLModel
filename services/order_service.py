from __future__ import annotations

from typing import Iterable
import json

from sqlmodel import Session

from db.order_config import order_request_engine, order_data_engine
from db.order_models import OrderRequest
from repositories import order_request_repository, order_pending_repository, order_repository


class OrderService:
    def submit_request(self, origin: str, df) -> OrderRequest:
        total = len(df.index) if hasattr(df, "index") else 0
        desc = f"{total} ordens processadas aguardando confirmação."
        with Session(order_request_engine) as req_session:
            req = order_request_repository.create_request(
                req_session,
                origin=origin,
                description=desc,
                total_orders=total,
            )
            order_pending_repository.save_pending(req_session, origin, req.id, df)
            req_session.refresh(req)
            return req

    def approve(self, request_id: int, approve: bool) -> None:
        with Session(order_request_engine) as req_session:
            req = order_request_repository.get_by_id(req_session, request_id)
            if req is None:
                raise ValueError("Solicitação não encontrada.")
            origin = req.origin
            if not approve:
                order_pending_repository.delete_by_request(req_session, origin, request_id)
                order_request_repository.update_status(req_session, req, "recusado")
                return

            pending_rows = order_pending_repository.list_by_request(req_session, origin, request_id)
            rows_data = [row.dict() for row in pending_rows]
            order_request_repository.update_status(req_session, req, "aprovado")

        if approve:
            with Session(order_data_engine) as data_session:
                order_repository.upsert_orders(data_session, origin, rows_data)

            with Session(order_request_engine) as cleanup_session:
                order_pending_repository.delete_by_request(cleanup_session, origin, request_id)
