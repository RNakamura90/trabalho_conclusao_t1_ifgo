from pathlib import Path
import zipfile
import pandas as pd

def list_zip_files(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path, "r") as z:
        return z.namelist()


def read_csv_from_zip(
    zip_path: Path,
    file_name: str,
    sep: str = ";",
    encoding: str = "latin1",
) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path, "r") as z:
        if file_name not in z.namelist():
            raise FileNotFoundError(f"Arquivo não encontrado no ZIP: {file_name}")

        with z.open(file_name) as f:
            df = pd.read_csv(
                f,
                sep=sep,
                encoding=encoding,
                dtype=str,
                low_memory=False,
            )

    df["ARQUIVO_ORIGEM"] = file_name
    return df


def read_brasil_file(zip_path: Path, prefix: str) -> pd.DataFrame:
    file_name = f"{prefix}_BRASIL.csv"
    return read_csv_from_zip(zip_path, file_name)


def parse_money(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )


def filter_by_cargo(df: pd.DataFrame, cargo: str) -> pd.DataFrame:
    return df[
        df["DS_CARGO"].str.upper().eq(cargo.upper())
    ].copy()


def filter_by_candidate_name(
    df: pd.DataFrame,
    patterns: list[str],
    column: str = "NM_CANDIDATO",
) -> pd.DataFrame:
    pattern = "|".join(patterns)

    return df[
        df[column]
        .str.upper()
        .str.contains(pattern, na=False)
    ].copy()
    

def normalize_text(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .str.upper()
        .replace({"NAN": pd.NA, "": pd.NA})
    )


def parse_money(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .replace({"nan": None, "": None})
        .astype(float)
    )


def filter_presidential_candidates(
    df: pd.DataFrame,
    candidate_numbers: list[str] | None = None,
) -> pd.DataFrame:
    if candidate_numbers is None:
        candidate_numbers = ["13", "22"]

    out = df.copy()

    if "DS_CARGO" in out.columns:
        out = out[
            normalize_text(out["DS_CARGO"]).eq("PRESIDENTE")
        ].copy()

    if "NR_CANDIDATO" in out.columns:
        out = out[
            out["NR_CANDIDATO"].isin(candidate_numbers)
        ].copy()

    return out