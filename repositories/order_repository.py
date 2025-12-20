from __future__ import annotations

import json
from typing import Iterable, List

from sqlmodel import Session, select

from db.order_models import Order167, Order171


def _model(origin: str):
    if "167" in origin:
        return Order167
    return Order171


def upsert_orders(session: Session, origin: str, rows: Iterable) -> None:
    Model = _model(origin)
    seen = set()
    for row in rows:
        data = row if isinstance(row, dict) else row.dict()
        data.pop("request_id", None)
        nro_ordem = str(data.get("nro_ordem") or "").strip()
        if not nro_ordem:
            continue
        if nro_ordem in seen:
            continue
        seen.add(nro_ordem)
        if session.get(Model, nro_ordem) is not None:
            continue  # preserve existing in DB
        obj = Model(**data)
        session.add(obj)
    session.commit()


def list_all(session: Session, origin: str) -> List:
    Model = _model(origin)
    stmt = select(Model)
    return list(session.exec(stmt).all())
