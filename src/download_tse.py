from pathlib import Path
import requests


TSE_URL = (
    "https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/"
    "prestacao_de_contas_eleitorais_candidatos_2022.zip"
)


def download_file(url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        print(f"Arquivo já existe: {output_path}")
        return

    print("Baixando arquivo...")
    response = requests.get(url, timeout=120)
    response.raise_for_status()

    output_path.write_bytes(response.content)
    print(f"Arquivo salvo em: {output_path}")


if __name__ == "__main__":
    zip_path = Path("data/raw/prestacao_de_contas_eleitorais_candidatos_2022.zip")
    download_file(TSE_URL, zip_path)