# Travelling-Salesman-Problem
Trabalho de Gerenciamento de Recursos Computacionais

k-TSP do turno de um entregador de moto resolvido com **Simulated Annealing** (enunciado em [`docs/Enunciado.md`](docs/Enunciado.md)).

## Como executar

Requer [uv](https://docs.astral.sh/uv/).

```bash
uv sync                                    # instala dependências
uv run streamlit run app/streamlit_app.py  # aplicação demonstrativa
uv run python experiments/run.py           # experimentos (saída em experiments/results/)
uv run pytest                              # testes
uv run ruff check . && uv run ruff format --check .  # análise estática
```

## Estrutura

| Caminho | Conteúdo |
| --- | --- |
| `src/ktsp/instance.py` | Instância (grafo, base, W) e gerador de cidades sintéticas |
| `src/ktsp/distances.py` | Menores caminhos (Dijkstra) entre base e pontos de entrega |
| `src/ktsp/solution.py` | Custo da rota e expansão no caminho completo |
| `src/ktsp/annealing.py` | Simulated Annealing (vizinho 2-opt, resfriamento geométrico) |
| `src/ktsp/baselines.py` | Vizinho mais próximo e força bruta (referências) |
| `app/streamlit_app.py` | Aplicação que anima a busca do SA |
| `experiments/run.py` | Experimentos variando k e α |

## Uso de IA Generativa

O projeto usa Claude Code; as instruções dadas à IA estão em [`CLAUDE.md`](CLAUDE.md).
