from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

from sqlmodel import SQLModel, create_engine

from .order_models import (
    OrderRequest,
    Order167Pending,
    Order171Pending,
    Order167,
    Order171,
)

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _base_dir()
ORDER_REQUEST_DB_PATH = BASE_DIR / "data" / "order_requests.db"
ORDER_DATA_DB_PATH = BASE_DIR / "data" / "orders.db"

order_request_engine = create_engine(
    f"sqlite:///{ORDER_REQUEST_DB_PATH}", echo=False, connect_args={"check_same_thread": False}
)

order_data_engine = create_engine(
    f"sqlite:///{ORDER_DATA_DB_PATH}", echo=False, connect_args={"check_same_thread": False}
)


def _create_tables(engine, tables: Iterable) -> None:
    SQLModel.metadata.create_all(engine, tables=list(tables))


def init_order_request_db() -> None:
    ORDER_REQUEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _create_tables(order_request_engine, [OrderRequest.__table__, Order167Pending.__table__, Order171Pending.__table__])


def init_order_data_db() -> None:
    ORDER_DATA_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _create_tables(order_data_engine, [Order167.__table__, Order171.__table__])
