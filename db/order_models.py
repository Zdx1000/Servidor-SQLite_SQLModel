from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, String, Text
from sqlmodel import Field, SQLModel


class OrderRequest(SQLModel, table=True):
    __tablename__ = "order_requests"

    id: int | None = Field(default=None, primary_key=True)
    origin: str = Field(nullable=False, max_length=64)
    description: str = Field(nullable=False, max_length=1024)
    total_orders: int | None = Field(default=None)
    status: str = Field(default="pendente", nullable=False, max_length=32)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class Order167Pending(SQLModel, table=True):
    __tablename__ = "order_167_pending"

    nro_ordem: str = Field(
        sa_column=Column("Nro Ordem", String, primary_key=True),
        description="Identificador principal da ordem",
    )
    status: str | None = Field(default=None, sa_column=Column("STATUS", String))
    tratativa: str | None = Field(default=None, sa_column=Column("TRATATIVA", String))
    responsavel: str | None = Field(default=None, sa_column=Column("Responsável", String))
    data_fechamento_div: datetime | None = Field(default=None, sa_column=Column("Data Fechamento Divergência", String))
    conferente: str | None = Field(default=None, sa_column=Column("Conferente", String))
    obs: str | None = Field(default=None, sa_column=Column("OBS", Text))
    obs2: str | None = Field(default=None, sa_column=Column("OBS - 2", Text))
    regiao: str | None = Field(default=None, sa_column=Column("Região", String))
    filial_contabil: str | None = Field(default=None, sa_column=Column("Filial Contábil", String))
    tipo_devolucao: str | None = Field(default=None, sa_column=Column("Tipo Devol.", String))
    carga: str | None = Field(default=None, sa_column=Column("Carga", String))
    valor: float | None = Field(default=None, sa_column=Column("Valor", String))
    falta: float | None = Field(default=None, sa_column=Column("Falta", String))
    mes: int | None = Field(default=None, sa_column=Column("MÊS", String))
    semana: int | None = Field(default=None, sa_column=Column("Semana", String))
    data_ordem: datetime | None = Field(default=None, sa_column=Column("Data Ordem", String))
    data_limite: datetime | None = Field(default=None, sa_column=Column("DATA LIMITE", String))
    mes_fech: int | None = Field(default=None, sa_column=Column("MÊS DE FECH", String))
    ano: int | None = Field(default=None, sa_column=Column("ANO", String))
    semana_limit: str | None = Field(default=None, sa_column=Column("Semana-Limit", String))
    cod_regiao: str | None = Field(default=None, sa_column=Column("Cód. Região", String))
    regiao2: str | None = Field(default=None, sa_column=Column("Região - 2", String))
    gerencia: str | None = Field(default=None, sa_column=Column("Gerencia", String))
    stt: str | None = Field(default=None, sa_column=Column("STT", String))
    email: str | None = Field(default=None, sa_column=Column("Email", String))
    dias_vencer: int | None = Field(default=None, sa_column=Column("Dias a Vencer", String))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    request_id: int = Field(nullable=False, index=True)


class Order171Pending(SQLModel, table=True):
    __tablename__ = "order_171_pending"

    nro_ordem: str = Field(
        sa_column=Column("Nro Ordem", String, primary_key=True),
        description="Identificador principal da ordem",
    )
    status: str | None = Field(default=None, sa_column=Column("Status", String))
    tratativa: str | None = Field(default=None, sa_column=Column("Tratativa", String))
    nome: str | None = Field(default=None, sa_column=Column("Nome", String))
    data_tratativa: datetime | None = Field(default=None, sa_column=Column("Data Tratativa", String))
    cliente: str | None = Field(default=None, sa_column=Column("Cliente", String))
    cod_cli: str | None = Field(default=None, sa_column=Column("Cód. Cli", String))
    tipo_devolucao: str | None = Field(default=None, sa_column=Column("Tipo Devol.", String))
    carga: str | None = Field(default=None, sa_column=Column("Carga", String))
    valor: float | None = Field(default=None, sa_column=Column("Valor", String))
    mes: int | None = Field(default=None, sa_column=Column("MÊS", String))
    ano: int | None = Field(default=None, sa_column=Column("ANO", String))
    semana: int | None = Field(default=None, sa_column=Column("Semana", String))
    data_ordem: datetime | None = Field(default=None, sa_column=Column("Data Ordem", String))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    request_id: int = Field(nullable=False, index=True)


class Order167(SQLModel, table=True):
    __tablename__ = "orders_167"

    nro_ordem: str = Field(
        sa_column=Column("Nro Ordem", String, primary_key=True),
        description="Identificador principal da ordem",
    )
    status: str | None = Field(default=None, sa_column=Column("STATUS", String))
    tratativa: str | None = Field(default=None, sa_column=Column("TRATATIVA", String))
    responsavel: str | None = Field(default=None, sa_column=Column("Responsável", String))
    data_fechamento_div: datetime | None = Field(default=None, sa_column=Column("Data Fechamento Divergência", String))
    conferente: str | None = Field(default=None, sa_column=Column("Conferente", String))
    obs: str | None = Field(default=None, sa_column=Column("OBS", Text))
    obs2: str | None = Field(default=None, sa_column=Column("OBS - 2", Text))
    regiao: str | None = Field(default=None, sa_column=Column("Região", String))
    filial_contabil: str | None = Field(default=None, sa_column=Column("Filial Contábil", String))
    tipo_devolucao: str | None = Field(default=None, sa_column=Column("Tipo Devol.", String))
    carga: str | None = Field(default=None, sa_column=Column("Carga", String))
    valor: float | None = Field(default=None, sa_column=Column("Valor", String))
    falta: float | None = Field(default=None, sa_column=Column("Falta", String))
    mes: int | None = Field(default=None, sa_column=Column("MÊS", String))
    semana: int | None = Field(default=None, sa_column=Column("Semana", String))
    data_ordem: datetime | None = Field(default=None, sa_column=Column("Data Ordem", String))
    data_limite: datetime | None = Field(default=None, sa_column=Column("DATA LIMITE", String))
    mes_fech: int | None = Field(default=None, sa_column=Column("MÊS DE FECH", String))
    ano: int | None = Field(default=None, sa_column=Column("ANO", String))
    semana_limit: str | None = Field(default=None, sa_column=Column("Semana-Limit", String))
    cod_regiao: str | None = Field(default=None, sa_column=Column("Cód. Região", String))
    regiao2: str | None = Field(default=None, sa_column=Column("Região - 2", String))
    gerencia: str | None = Field(default=None, sa_column=Column("Gerencia", String))
    stt: str | None = Field(default=None, sa_column=Column("STT", String))
    email: str | None = Field(default=None, sa_column=Column("Email", String))
    dias_vencer: int | None = Field(default=None, sa_column=Column("Dias a Vencer", String))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class Order171(SQLModel, table=True):
    __tablename__ = "orders_171"

    nro_ordem: str = Field(
        sa_column=Column("Nro Ordem", String, primary_key=True),
        description="Identificador principal da ordem",
    )
    status: str | None = Field(default=None, sa_column=Column("Status", String))
    tratativa: str | None = Field(default=None, sa_column=Column("Tratativa", String))
    nome: str | None = Field(default=None, sa_column=Column("Nome", String))
    data_tratativa: datetime | None = Field(default=None, sa_column=Column("Data Tratativa", String))
    cliente: str | None = Field(default=None, sa_column=Column("Cliente", String))
    cod_cli: str | None = Field(default=None, sa_column=Column("Cód. Cli", String))
    tipo_devolucao: str | None = Field(default=None, sa_column=Column("Tipo Devol.", String))
    carga: str | None = Field(default=None, sa_column=Column("Carga", String))
    valor: float | None = Field(default=None, sa_column=Column("Valor", String))
    mes: int | None = Field(default=None, sa_column=Column("MÊS", String))
    ano: int | None = Field(default=None, sa_column=Column("ANO", String))
    semana: int | None = Field(default=None, sa_column=Column("Semana", String))
    data_ordem: datetime | None = Field(default=None, sa_column=Column("Data Ordem", String))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
