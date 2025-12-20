from __future__ import annotations

from typing import Iterable, List

from sqlmodel import Session, select

from datetime import datetime
from typing import Any, Dict

from db.order_models import Order167Pending, Order171Pending


def _to_datetime(val: Any) -> datetime | None:
    try:
        import pandas as pd

        if isinstance(val, pd.Timestamp):
            return val.to_pydatetime()
    except Exception:
        pass
    if isinstance(val, datetime):
        return val
    if val is None:
        return None
    try:
        return datetime.fromisoformat(str(val))
    except Exception:
        return None


def _pending_model(origin: str):
    if "167" in origin:
        return Order167Pending
    return Order171Pending


def _normalize_167(rec: Dict, request_id: int) -> Dict:
    return {
        "nro_ordem": str(rec.get("Nro Ordem", "")).strip(),
        "status": rec.get("STATUS"),
        "tratativa": rec.get("TRATATIVA"),
        "responsavel": rec.get("Responsável"),
        "data_fechamento_div": _to_datetime(rec.get("Data Fechamento Divergência")),
        "conferente": rec.get("Conferente"),
        "obs": rec.get("OBS"),
        "obs2": rec.get("OBS - 2"),
        "regiao": rec.get("Região"),
        "filial_contabil": rec.get("Filial Contábil"),
        "tipo_devolucao": rec.get("Tipo Devol."),
        "carga": rec.get("Carga"),
        "valor": _to_float(rec.get("Valor")),
        "falta": _to_float(rec.get("Falta")),
        "mes": _to_int(rec.get("MÊS")),
        "semana": _to_int(rec.get("Semana")),
        "data_ordem": _to_datetime(rec.get("Data Ordem")),
        "data_limite": _to_datetime(rec.get("DATA LIMITE")),
        "mes_fech": _to_int(rec.get("MÊS DE FECH")),
        "ano": _to_int(rec.get("ANO")),
        "semana_limit": rec.get("Semana-Limit"),
        "cod_regiao": rec.get("Cód. Região"),
        "regiao2": rec.get("Região - 2"),
        "gerencia": rec.get("Gerencia"),
        "stt": rec.get("STT"),
        "email": rec.get("Email"),
        "dias_vencer": _to_int(rec.get("Dias a Vencer")),
        "request_id": request_id,
    }


def _normalize_171(rec: Dict, request_id: int) -> Dict:
    return {
        "nro_ordem": str(rec.get("Nro Ordem", "")).strip(),
        "status": rec.get("Status"),
        "tratativa": rec.get("Tratativa"),
        "nome": rec.get("Nome"),
        "data_tratativa": _to_datetime(rec.get("Data Tratativa")),
        "cliente": rec.get("Cliente"),
        "cod_cli": rec.get("Cód. Cli"),
        "tipo_devolucao": rec.get("Tipo Devol."),
        "carga": rec.get("Carga"),
        "valor": _to_float(rec.get("Valor")),
        "mes": _to_int(rec.get("MÊS")),
        "ano": _to_int(rec.get("ANO")),
        "semana": _to_int(rec.get("Semana")),
        "data_ordem": _to_datetime(rec.get("Data Ordem")),
        "request_id": request_id,
    }


def _to_int(val: Any) -> int | None:
    try:
        if val is None:
            return None
        return int(val)
    except Exception:
        return None


def _to_float(val: Any) -> float | None:
    try:
        if val is None or str(val).strip() == "":
            return None
        return float(str(val).replace(",", "."))
    except Exception:
        return None


def save_pending(session: Session, origin: str, request_id: int, df) -> None:
    Model = _pending_model(origin)
    records = df.to_dict(orient="records") if hasattr(df, "to_dict") else []
    for rec in records:
        nro = rec.get("Nro Ordem")
        if not nro:
            continue
        data = _normalize_167(rec, request_id) if Model is Order167Pending else _normalize_171(rec, request_id)
        obj = Model(**data)
        session.merge(obj)
    session.commit()


def list_by_request(session: Session, origin: str, request_id: int) -> List:
    Model = _pending_model(origin)
    stmt = select(Model).where(Model.request_id == request_id)
    return list(session.exec(stmt).all())


def delete_by_request(session: Session, origin: str, request_id: int) -> None:
    Model = _pending_model(origin)
    stmt = select(Model).where(Model.request_id == request_id)
    rows: Iterable[Model] = session.exec(stmt)
    for row in rows:
        session.delete(row)
    session.commit()
