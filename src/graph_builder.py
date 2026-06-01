import pandas as pd
import networkx as nx


def make_node(label: str, node_type: str) -> str:
    return f"{node_type}::{label}"


def money_to_cost(value: float) -> float:
    if pd.isna(value) or value <= 0:
        return 1.0

    return 1 / (1 + value)


def build_campaign_graph(
    receitas_com_originario: pd.DataFrame,
    despesas_pres: pd.DataFrame,
) -> nx.DiGraph:
    G = nx.DiGraph()

    for _, row in receitas_com_originario.iterrows():
        candidato = make_node(row["NM_CANDIDATO"], "candidato")
        fonte = make_node(row["DS_FONTE_RECEITA"], "fonte_receita")
        origem = make_node(row["DS_ORIGEM_RECEITA"], "origem_receita")

        valor = row["VR_RECEITA_NUM"]
        custo = money_to_cost(valor)

        G.add_edge(origem, fonte, tipo="origem_fonte", valor=valor, weight=custo)
        G.add_edge(fonte, candidato, tipo="fonte_candidato", valor=valor, weight=custo)

        if pd.notna(row.get("NM_DOADOR")):
            doador = make_node(row["NM_DOADOR"], "doador_direto")
            G.add_edge(doador, origem, tipo="doador_origem", valor=valor, weight=custo)

        if pd.notna(row.get("NM_DOADOR_ORIGINARIO")):
            doador_originario = make_node(row["NM_DOADOR_ORIGINARIO"], "doador_originario")
            G.add_edge(doador_originario, origem, tipo="doador_originario_origem", valor=valor, weight=custo)

    for _, row in despesas_pres.iterrows():
        candidato = make_node(row["NM_CANDIDATO"], "candidato")
        tipo_despesa = make_node(row["DS_ORIGEM_DESPESA"], "tipo_despesa")
        fornecedor = make_node(row["NM_FORNECEDOR"], "fornecedor")

        valor = row["VR_DESPESA_CONTRATADA_NUM"]
        custo = money_to_cost(valor)

        G.add_edge(candidato, tipo_despesa, tipo="candidato_tipo_despesa", valor=valor, weight=custo)
        G.add_edge(tipo_despesa, fornecedor, tipo="tipo_despesa_fornecedor", valor=valor, weight=custo)

        if pd.notna(row.get("DS_CNAE_FORNECEDOR")):
            cnae = make_node(row["DS_CNAE_FORNECEDOR"], "cnae_fornecedor")
            G.add_edge(fornecedor, cnae, tipo="fornecedor_cnae", valor=valor, weight=custo)

    return G