from pathlib import Path
import zipfile


ZIP_PATH = Path("data/raw/prestacao_de_contas_eleitorais_candidatos_2022.zip")


def inspect_zip(zip_path: Path) -> None:
    if not zip_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {zip_path}")

    with zipfile.ZipFile(zip_path, "r") as z:
        files = z.namelist()

    print(f"Total de arquivos no ZIP: {len(files)}")
    print("\nArquivos encontrados:\n")

    for file in files:
        print(file)


if __name__ == "__main__":
    inspect_zip(ZIP_PATH)