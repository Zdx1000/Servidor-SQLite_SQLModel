import pandas as pd

class AdicionarOrdensNovas2:
    def __init__(self, file_path: str) -> None:

        self.file_path = file_path

        COLS = [
            "Nro Ordem", "Status", "Tratativa", "Nome", "Data Tratativa",
            "Cliente", "Cód. Cli", "Tipo Devol.", "Carga", "Valor",
            "MÊS", "ANO", "Semana", "Data Ordem"
        ]

        self.COLS = COLS

        TIPOS_OK = {"Devolução CORTE", "Bonificação CORTE"}
        self.TIPOS_OK = TIPOS_OK

    def load_xlsx(self):

        return pd.read_excel(self.file_path, engine="openpyxl")

    def Manipular_Dados(self, df: pd.DataFrame | None = None) -> pd.DataFrame | str | None:
        if df is None or df.empty:
            return df

        if "Tipo Devol." in df.columns:
            df = df[df["Tipo Devol."].isin(self.TIPOS_OK)]


        df = df.reindex(columns=self.COLS, fill_value="")

        dt = pd.to_datetime(df["Data Ordem"], dayfirst=True, errors="coerce")
        df["Data Ordem"] = dt
        df["MÊS"] = dt.dt.month
        df["ANO"] = dt.dt.year
        df["Semana"] = dt.dt.isocalendar().week

        s = df["Valor"]
        df["Valor"] = pd.to_numeric(
            s.astype(str).str.replace(",", ".", regex=False),
            errors="coerce"
        ).fillna(0.0)

        df["Status"] = ""

        return df


if __name__ == "__main__":
    # exemplo de uso
    adicionar_ordens_novas = AdicionarOrdensNovas2("Orden.xlsx")
    df = adicionar_ordens_novas.load_xlsx()
    df_tratado = adicionar_ordens_novas.Manipular_Dados(df=df)
    print(df_tratado.head())