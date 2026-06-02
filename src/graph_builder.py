import pandas as pd
import networkx as nx
import numpy as np


def make_node(label, node_type):
    if pd.isna(label):
        return None

    label = str(label).strip()

    if label == "" or label.upper() in ["NAN", "#NULO"]:
        return None

    return f"{node_type}::{label}"


def money_to_cost(value: float) -> float:
    if pd.isna(value) or value <= 0:
        return 1.0

    return 1 / (1 + np.log1p(value))

def aggregate_edges(edges):
    edges = edges.dropna(subset=["source", "target", "tipo"]).copy()

    edges = (
        edges
        .groupby(["source", "target", "tipo"], as_index=False)
        .agg(
            valor_total=("valor", "sum"),
            qtd_registros=("valor", "size"),
        )
    )

    edges["weight"] = edges["valor_total"].apply(money_to_cost)

    return edges


def build_campaign_graph_v2(
    receitas_com_originario: pd.DataFrame,
    despesas_pres: pd.DataFrame,
) -> tuple[nx.DiGraph, pd.DataFrame]:

    revenue_edges = build_revenue_edges(receitas_com_originario)
    expense_edges = build_expense_edges(despesas_pres)

    edges_raw = pd.concat(
        
        [revenue_edges, expense_edges],
        ignore_index=True,
    )

    edges = aggregate_edges(edges_raw)

    G = nx.DiGraph()

    for _, row in edges.iterrows():
        G.add_edge(
            row["source"],
            row["target"],
            tipo=row["tipo"],
            valor_total=row["valor_total"],
            qtd_registros=row["qtd_registros"],
            weight=row["weight"],
        )

    return G, edges

def build_revenue_edges(receitas_com_originario: pd.DataFrame) -> pd.DataFrame:
    edges = []

    for _, row in receitas_com_originario.iterrows():
        candidato = make_node(row.get("NM_CANDIDATO"), "candidato")
        fonte = make_node(row.get("DS_FONTE_RECEITA"), "fonte_receita")
        origem = make_node(row.get("DS_ORIGEM_RECEITA"), "origem_receita")
        doador = make_node(row.get("NM_DOADOR"), "doador_direto")
        doador_originario = make_node(row.get("NM_DOADOR_ORIGINARIO"), "doador_originario")

        valor = row.get("VR_RECEITA_NUM", 0)

        if origem and fonte:
            edges.append({
                "source": origem,
                "target": fonte,
                "tipo": "origem_fonte",
                "valor": valor,
            })

        if fonte and candidato:
            edges.append({
                "source": fonte,
                "target": candidato,
                "tipo": "fonte_candidato",
                "valor": valor,
            })

        if doador and origem:
            edges.append({
                "source": doador,
                "target": origem,
                "tipo": "doador_origem",
                "valor": valor,
            })

        if doador_originario and origem:
            edges.append({
                "source": doador_originario,
                "target": origem,
                "tipo": "doador_originario_origem",
                "valor": valor,
            })

    return pd.DataFrame(edges)

def build_expense_edges(despesas_pres: pd.DataFrame) -> pd.DataFrame:
    edges = []

    for _, row in despesas_pres.iterrows():
        candidato = make_node(row.get("NM_CANDIDATO"), "candidato")
        tipo_despesa = make_node(row.get("DS_ORIGEM_DESPESA"), "tipo_despesa")
        fornecedor = make_node(row.get("NM_FORNECEDOR"), "fornecedor")
        cnae = make_node(row.get("DS_CNAE_FORNECEDOR"), "cnae_fornecedor")

        valor = row.get("VR_DESPESA_CONTRATADA_NUM", 0)

        if candidato and tipo_despesa:
            edges.append({
                "source": candidato,
                "target": tipo_despesa,
                "tipo": "candidato_tipo_despesa",
                "valor": valor,
            })

        if tipo_despesa and fornecedor:
            edges.append({
                "source": tipo_despesa,
                "target": fornecedor,
                "tipo": "tipo_despesa_fornecedor",
                "valor": valor,
            })

        if fornecedor and cnae:
            edges.append({
                "source": fornecedor,
                "target": cnae,
                "tipo": "fornecedor_cnae",
                "valor": valor,
            })

    return pd.DataFrame(edges)

def build_category_edges(receitas_pres, despesas_pres):
    edges = []

    for _, row in receitas_pres.iterrows():
        cnae_doador = make_node(row.get("DS_CNAE_DOADOR"), "cnae_doador")
        origem = make_node(row.get("DS_ORIGEM_RECEITA"), "origem_receita")
        fonte = make_node(row.get("DS_FONTE_RECEITA"), "fonte_receita")
        partido = make_node(row.get("SG_PARTIDO"), "partido")
        candidato = make_node(row.get("NM_CANDIDATO"), "candidato")

        valor = row.get("VR_RECEITA_NUM", 0)

        if cnae_doador and origem:
            edges.append({
                "source": cnae_doador,
                "target": origem,
                "tipo": "cnae_doador_origem",
                "valor": valor,
            })

        if origem and fonte:
            edges.append({
                "source": origem,
                "target": fonte,
                "tipo": "origem_fonte",
                "valor": valor,
            })

        if fonte and partido:
            edges.append({
                "source": fonte,
                "target": partido,
                "tipo": "fonte_partido",
                "valor": valor,
            })

        if partido and candidato:
            edges.append({
                "source": partido,
                "target": candidato,
                "tipo": "partido_candidato",
                "valor": valor,
            })

    for _, row in despesas_pres.iterrows():
        candidato = make_node(row.get("NM_CANDIDATO"), "candidato")
        tipo_despesa = make_node(row.get("DS_ORIGEM_DESPESA"), "tipo_despesa")
        cnae_fornecedor = make_node(row.get("DS_CNAE_FORNECEDOR"), "cnae_fornecedor")

        valor = row.get("VR_DESPESA_CONTRATADA_NUM", 0)

        if candidato and tipo_despesa:
            edges.append({
                "source": candidato,
                "target": tipo_despesa,
                "tipo": "candidato_tipo_despesa",
                "valor": valor,
            })

        if tipo_despesa and cnae_fornecedor:
            edges.append({
                "source": tipo_despesa,
                "target": cnae_fornecedor,
                "tipo": "tipo_despesa_cnae_fornecedor",
                "valor": valor,
            })

    return pd.DataFrame(edges)

def build_category_graph(receitas_pres, despesas_pres):
    raw_edges = build_category_edges(receitas_pres, despesas_pres)
    edges = aggregate_edges(raw_edges)

    G = nx.DiGraph()

    for _, row in edges.iterrows():
        G.add_edge(
            row["source"],
            row["target"],
            tipo=row["tipo"],
            valor_total=row["valor_total"],
            qtd_registros=row["qtd_registros"],
            weight=row["weight"],
        )

    return G, edges