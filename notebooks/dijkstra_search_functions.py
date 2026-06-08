# Função utilizada para baixar o arquivo zip do TSE, caso ele não exista localmente
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

# Função utilizada para ler um arquivo CSV específico de dentro do zip baixado do TSE    
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

# Função utilizada para listar os arquivos contidos no zip baixado do TSE    
def list_zip_files(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path, "r") as z:
        return z.namelist()

# Função utilizada para ler o arquivo Brasil do zip baixado do TSE
def read_brasil_file(zip_path: Path, prefix: str) -> pd.DataFrame:
    file_name = f"{prefix}_BRASIL.csv"
    return read_csv_from_zip(zip_path, file_name)

# Função utilizada para filtrar os candidatos presidenciais do DataFrame (apenas os candidatos com os números 13 e 22 (Lula e Bolsonaro))
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

# Função parse para valores monetários, convertendo os valores de string para float, considerando o formato brasileiro
def parse_money(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )
    
# Função para construção do grafo de categorias, utilizando as funções auxiliares para construir as arestas e agregá-las   
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

#Função para limpar os rótulos dos nós, removendo o prefixo de categoria (ex: "categoria::") para uma visualização mais limpa nos gráficos
def clean_label(node):
    return node.split("::", 1)[1] if "::" in node else node

#Função para extrair o subgrafo de um candidato específico, incluindo as arestas de entrada, saída, e as arestas conectadas aos nós vizinhos (upstream e downstream)
def get_candidate_subgraph_edges(edges, candidate_name):
    candidate_node = f"candidato::{candidate_name}"

    incoming = edges[
        edges["target"].eq(candidate_node)
    ].copy()

    outgoing = edges[
        edges["source"].eq(candidate_node)
    ].copy()

    previous_nodes = incoming["source"].unique()

    upstream = edges[
        edges["target"].isin(previous_nodes)
    ].copy()

    next_nodes = outgoing["target"].unique()

    downstream = edges[
        edges["source"].isin(next_nodes)
    ].copy()

    candidate_edges = pd.concat(
        [upstream, incoming, outgoing, downstream],
        ignore_index=True
    ).drop_duplicates()

    return candidate_edges

#Função para plotar o gráfico de Sankey para um candidato específico, utilizando o subgrafo extraído pela função anterior, e considerando apenas as top_n arestas mais relevantes
def plot_candidate_sankey(edges, candidate_name, top_n=40):
    df = get_candidate_subgraph_edges(edges, candidate_name)

    df = df.sort_values("valor_total", ascending=False).head(top_n)

    labels = pd.Index(
        pd.concat([df["source"], df["target"]]).unique()
    )

    node_id = {label: i for i, label in enumerate(labels)}

    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    label=[clean_label(x) for x in labels],
                    pad=15,
                    thickness=15,
                ),
                link=dict(
                    source=df["source"].map(node_id),
                    target=df["target"].map(node_id),
                    value=df["valor_total"],
                    customdata=df["tipo"],
                    hovertemplate=(
                        "Origem: %{source.label}<br>"
                        "Destino: %{target.label}<br>"
                        "Valor: R$ %{value:,.2f}<br>"
                        "Tipo: %{customdata}<extra></extra>"
                    ),
                ),
            )
        ]
    )

    fig.update_layout(
        title_text=f"Fluxo agregado da campanha: {candidate_name}",
        font_size=10,
        height=700,
    )

    return fig

#Função para calcular o custo total de um caminho no grafo, somando os pesos das arestas ao longo do caminho
def path_cost(G, path):
    cost = 0

    for i in range(len(path) - 1):
        cost += G[path[i]][path[i + 1]]["weight"]

    return cost

#Função para encontrar os caminhos mais curtos (com menor custo) entre as origens de receita e os destinos de fornecedores, passando por um candidato específico
def candidate_paths(
    G,
    candidate_name,
):
    candidate_node = f"candidato::{candidate_name}"

    origens = [
        n for n in G.nodes
        if n.startswith("origem_receita::")
    ]

    destinos = [
        n for n in G.nodes
        if n.startswith("cnae_fornecedor::")
    ]

    rows = []

    for origem in origens:
        for destino in destinos:

            try:
                path = nx.shortest_path( #Dijkstra
                    G,
                    source=origem,
                    target=destino,
                    weight="weight",
                )

                if candidate_node not in path:
                    continue

                rows.append({
                    "origem": origem,
                    "destino": destino,
                    "candidato": candidate_name,
                    "custo": path_cost(G, path),
                    "caminho": " -> ".join(path),
                    "num_passos": len(path) - 1,
                })

            except nx.NetworkXNoPath:
                pass

    return pd.DataFrame(rows)

#Função para descrever um caminho específico no grafo, detalhando as arestas e seus atributos ao longo do caminho
def describe_path(G, path):
    rows = []

    for i in range(len(path) - 1):
        source = path[i]
        target = path[i + 1]
        edge = G[source][target]

        rows.append({
            "step": i + 1,
            "source": source,
            "target": target,
            "tipo": edge["tipo"],
            "valor_total": edge["valor_total"],
            "qtd_registros": edge["qtd_registros"],
            "weight": edge["weight"],
        })

    return pd.DataFrame(rows)