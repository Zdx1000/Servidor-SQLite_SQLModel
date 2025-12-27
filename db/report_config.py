from __future__ import annotations

import sys
from pathlib import Path
from sqlmodel import SQLModel, create_engine

from db.report_models import ReportRequest

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _base_dir()
REPORT_DB_PATH = BASE_DIR / "data" / "reports.db"
REPORT_DATABASE_URL = f"sqlite:///{REPORT_DB_PATH}"

report_engine = create_engine(
    REPORT_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_report_db() -> None:
    REPORT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(report_engine, tables=[ReportRequest.__table__])
