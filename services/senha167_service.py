from __future__ import annotations

import numpy as np
import pandas as pd
from pandas.tseries.offsets import CustomBusinessDay


class AdicionarOrdensNovas2:
    """Helper para importar e normalizar ordens do fluxo 167."""

    COLS = [
        "Nro Ordem",
        "STATUS",
        "TRATATIVA",
        "Responsável",
        "Data Fechamento Divergência",
        "Conferente",
        "OBS",
        "OBS - 2",
        "Região",
        "Filial Contábil",
        "Tipo Devol.",
        "Carga",
        "Valor",
        "Falta",
        "MÊS",
        "Semana",
        "Data Ordem",
        "DATA LIMITE",
        "MÊS DE FECH",
        "ANO",
        "Semana-Limit",
        "Cód. Região",
        "Região - 2",
        "Gerencia",
        "STT",
        "Email",
        "Dias a Vencer",
    ]

    FERIADOS_FIXOS_MD = [
        (1, 1),
        (4, 15),
        (4, 21),
        (5, 1),
        (9, 7),
        (10, 12),
        (11, 2),
        (11, 15),
        (12, 25),
        (12, 31),
    ]

    def __init__(self, file_path: str) -> None:
        self.file_path = str(file_path)

    def load_xlsx(self) -> pd.DataFrame:
        return pd.read_excel(self.file_path, engine="openpyxl")

    @staticmethod
    def _to_float_valor(s: pd.Series) -> pd.Series:
        return pd.to_numeric(s.astype("string").str.replace(",", ".", regex=False), errors="coerce").fillna(0.0)

    def Manipular_Dados(self, df: pd.DataFrame | None = None) -> pd.DataFrame | None:
        if df is None:
            df = self.load_xlsx()
        if df is None or df.empty:
            return df

        df = df.rename(columns={"Cliente": "Região", "Cód. Cli": "Filial Contábil"})
        df = df.reindex(columns=self.COLS, fill_value="")
        df["Responsável"] = df["Responsável"].fillna("")

        dt = pd.to_datetime(df["Data Ordem"], dayfirst=True, errors="coerce")
        df["Data Ordem"] = dt
        df["MÊS"] = dt.dt.month
        df["ANO"] = dt.dt.year
        df["Semana"] = dt.dt.isocalendar().week.astype("Int64")

        df["Valor"] = self._to_float_valor(df["Valor"])
        df["STATUS"] = ""

        falta = df["Falta"]
        mask_falta = falta.notna() & falta.astype("string").str.strip().ne("")
        df = df.loc[mask_falta].copy()

        dt2 = df["Data Ordem"]
        if dt2.notna().any():
            min_y = int(dt2.dt.year.min())
            max_y = int(dt2.dt.year.max()) + 1
            holidays = [pd.Timestamp(y, m, d) for y in range(min_y, max_y + 1) for (m, d) in self.FERIADOS_FIXOS_MD]
        else:
            holidays = []

        cbd = CustomBusinessDay(holidays=holidays)
        df["DATA LIMITE"] = df["Data Ordem"] + 7 * cbd

        df["MÊS DE FECH"] = df["DATA LIMITE"].dt.month

        week_lim = df["DATA LIMITE"].dt.isocalendar().week.astype("Int64")
        df["Semana-Limit"] = ("Sem. " + week_lim.astype("string")).where(df["DATA LIMITE"].notna(), "")

        today = pd.Timestamp.today().normalize()
        df["Dias a Vencer"] = (df["DATA LIMITE"] - today).dt.days.astype("Int64")

        df["STT"] = np.where(df["Valor"] < 50, "SEM EVIDENCIA", "COM EVIDENCIA")

        return df
