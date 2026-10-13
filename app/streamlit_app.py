"""Aplicação que demonstra o Simulated Annealing resolvendo o k-TSP.

Execução: ``uv run streamlit run app/streamlit_app.py``.
"""

import random
import time

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import streamlit as st
from matplotlib.figure import Figure

from ktsp.annealing import AnnealingParams, Step, anneal
from ktsp.baselines import MAX_BRUTE_FORCE_K, brute_force, nearest_neighbor
from ktsp.distances import DistanceTable, build_distance_table
from ktsp.instance import Instance, generate_instance
from ktsp.solution import Route

ANIMATION_FRAMES = 60


def draw_map(instance: Instance, table: DistanceTable, step: Step) -> Figure:
    """Desenha o grafo, a rota corrente (tracejada) e a melhor rota da iteração."""
    # pos é (linha, coluna); vira (x, y) com a linha 0 no topo
    pos = {n: (c, -r) for n, (r, c) in instance.graph.nodes(data="pos")}
    fig, ax = plt.subplots(figsize=(7, 7))
    nx.draw_networkx_edges(instance.graph, pos, ax=ax, edge_color="#cccccc")

    for order, style in ((step.current_order, "--"), (step.best_order, "-")):
        path = Route.from_order(order, table).path
        xs, ys = zip(*(pos[v] for v in path), strict=True)
        color = "#999999" if style == "--" else "#1f77b4"
        ax.plot(xs, ys, style, color=color, linewidth=2.5, alpha=0.9)

    nx.draw_networkx_nodes(
        instance.graph, pos, nodelist=list(instance.deliveries), node_color="#ff7f0e"
    )
    nx.draw_networkx_nodes(
        instance.graph,
        pos,
        nodelist=[instance.base],
        node_color="#d62728",
        node_size=500,
    )
    labels = {table.points[i]: n for n, i in enumerate(step.best_order, start=1)}
    labels[instance.base] = "B"
    nx.draw_networkx_labels(instance.graph, pos, labels, font_size=9, ax=ax)

    ax.set_title(
        f"Iteração {step.iteration} · T = {step.temperature:.3f} · "
        f"melhor = {step.best_cost:.0f} · corrente = {step.current_cost:.0f}"
    )
    ax.set_axis_off()
    return fig


def show_map(placeholder, instance: Instance, table: DistanceTable, step: Step) -> None:
    """Renderiza o mapa de uma iteração num espaço reservado da página."""
    fig = draw_map(instance, table, step)
    placeholder.pyplot(fig)
    plt.close(fig)


def history_frame(steps: list[Step]) -> pd.DataFrame:
    """Converte os passos do SA numa tabela com custos, temperatura e aceitação."""
    df = pd.DataFrame(
        {
            "iteração": [s.iteration for s in steps],
            "temperatura": [s.temperature for s in steps],
            "custo corrente": [s.current_cost for s in steps],
            "melhor custo": [s.best_cost for s in steps],
            "piora": [s.worse for s in steps],
            "piora aceita": [s.worse and s.accepted for s in steps],
        }
    ).set_index("iteração")
    window = max(1, len(df) // 50)
    df["taxa de aceitação de pioras"] = (
        df["piora aceita"].rolling(window).sum() / df["piora"].rolling(window).sum()
    )
    return df


st.set_page_config(page_title="k-TSP com Simulated Annealing", layout="wide")
st.title("Turno do entregador de moto · k-TSP com Simulated Annealing")

with st.expander("Como o Simulated Annealing funciona aqui"):
    st.markdown(
        """
- **Solução:** ordem de visita dos k pontos de entrega. A rota sai da base (B),
  segue a ordem pelos menores caminhos nas ruas e volta à base.
- **Vizinho:** inverte um trecho aleatório da ordem (movimento 2-opt).
- **Aceitação:** um vizinho melhor é sempre aceito; um pior, com probabilidade
  `exp(-Δ/T)`. Com T alta o algoritmo explora (aceita pioras); conforme
  `T ← α·T` esfria, ele passa a só melhorar.
- **Ponto de partida:** heurística do vizinho mais próximo.
"""
    )

with st.sidebar:
    st.header("Instância")
    seed = int(st.number_input("Semente", min_value=0, value=42))
    size = st.slider("Tamanho da grade (n × n)", 4, 25, 12)
    k = st.slider("Pontos de entrega (k)", 1, min(40, size * size - 1), 10)
    st.header("Simulated Annealing")
    params = AnnealingParams(
        initial_temperature=st.number_input("Temperatura inicial T0", 0.1, value=100.0),
        cooling_rate=st.slider("Resfriamento α", 0.9, 0.9999, 0.995, format="%.4f"),
        max_iterations=int(
            st.number_input("Máximo de iterações", 10, 200_000, 5000, step=500)
        ),
    )
    animate = st.checkbox("Animar a execução", value=True)
    run = st.button("Executar", type="primary", use_container_width=True)

if run:
    instance = generate_instance(size, size, k, seed)
    table = build_distance_table(instance)
    initial = nearest_neighbor(table)
    steps = list(anneal(table, initial, params, random.Random(seed)))
    optimum = brute_force(table) if k <= MAX_BRUTE_FORCE_K else None
    st.session_state.result = (instance, table, initial, steps, optimum)

if "result" not in st.session_state:
    st.info("Escolha os parâmetros na barra lateral e clique em **Executar**.")
    st.stop()

instance, table, initial, steps, optimum = st.session_state.result
history = history_frame(steps)
map_col, chart_col = st.columns([1, 1])

with map_col:
    placeholder = st.empty()
    if run and animate:
        for step in steps[:: max(1, len(steps) // ANIMATION_FRAMES)]:
            show_map(placeholder, instance, table, step)
            time.sleep(0.03)
    chosen = st.slider("Iteração", 0, len(steps) - 1, len(steps) - 1)
    show_map(placeholder, instance, table, steps[chosen])
    st.caption("Azul: melhor rota até a iteração · cinza tracejado: rota corrente.")

with chart_col:
    st.subheader("Custo")
    st.line_chart(history[["custo corrente", "melhor custo"]])
    st.subheader("Temperatura")
    st.line_chart(history["temperatura"])
    st.subheader("Taxa de aceitação de pioras")
    st.line_chart(history["taxa de aceitação de pioras"])

best = Route.from_order(steps[-1].best_order, table)
comparison = {
    "Vizinho mais próximo": Route.from_order(initial, table).cost,
    "Simulated Annealing": best.cost,
}
if optimum is not None:
    comparison["Ótimo (força bruta)"] = Route.from_order(optimum, table).cost
reference = comparison.get("Ótimo (força bruta)")

st.subheader("Comparação")
st.dataframe(
    pd.DataFrame(
        {
            "Distância": comparison,
            "Gap para o ótimo (%)": {
                name: 100 * (cost - reference) / reference if reference else None
                for name, cost in comparison.items()
            },
        }
    )
)
if optimum is None:
    st.caption(f"Ótimo calculado só para k ≤ {MAX_BRUTE_FORCE_K}.")

st.subheader("Rota entregue ao entregador")
st.markdown(f"**Distância total:** {best.cost:.0f}")
st.markdown(f"**Ordem de visita:** {' → '.join(map(str, best.visits))}")
st.markdown("**Caminho completo (vértice a vértice):**")
st.code(" → ".join(map(str, best.path)), wrap_lines=True)
