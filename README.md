# Travelling-Salesman-Problem

Planejamento da rota de um entregador de moto com **Simulated Annealing**. A rota precisa visitar um conjunto de pontos de entrega em uma cidade e voltar à base, percorrendo a menor distância possível.

Este README apresenta, em sequência:

1. o problema;
2. por que ele é difícil;
3. como ele foi modelado;
4. como o algoritmo o resolve;
5. como usar a aplicação que mostra o algoritmo funcionando.

---

## 1. O problema

No início do turno, um entregador de moto recebe da central uma lista de **k pontos de entrega**. Ele sai da **base**, passa por todos os pontos e volta à base. A pergunta é:

> **Em que ordem visitar os pontos para que a distância total seja a menor possível?**

A cidade é representada por um **grafo**:

- **vértices** são esquinas e pontos de entrega;
- **arestas** são ruas, e cada uma tem uma distância (peso).

O grafo **não liga todos os pares de pontos**. Para ir de uma entrega a outra, a moto em geral passa por várias esquinas intermediárias. Por isso a resposta não é só a ordem de visita, mas também o **caminho completo pelas ruas**.

Esse problema é uma variação do clássico **Problema do Caixeiro Viajante** (*Travelling Salesman Problem*, TSP), conhecida como **k-TSP**. Nela é preciso visitar exatamente os k pontos de uma lista, não todos os vértices do grafo.

## 2. Por que é difícil?

O TSP é **NP-difícil**: não se conhece algoritmo que encontre a melhor rota em tempo polinomial. A forma direta de resolvê-lo é testar todas as ordens possíveis, e o número de ordens cresce como k! (fatorial):

| Pontos (k) | Ordens possíveis (k!) |
| ---: | ---: |
| 5 | 120 |
| 8 | 40 320 |
| 10 | 3 628 800 |
| 15 | ≈ 1,3 × 10¹² |
| 30 | ≈ 2,7 × 10³² |

Com 30 entregas, testar todas as ordens é inviável. Por isso usamos uma **metaheurística**: um método que não garante o ótimo, mas encontra soluções muito boas em pouco tempo.

## 3. Modelagem

| Elemento | No problema |
| --- | --- |
| **Entrada** | Grafo conexo e ponderado G, vértice da base b e vetor W com os k pontos de entrega |
| **Solução** | Uma permutação π dos pontos de W (a ordem de visita) |
| **Rota** | b → W[π₁] → W[π₂] → … → W[πₖ] → b |
| **Objetivo** | Minimizar a distância total percorrida |
| **Restrições** | Cada ponto de W aparece exatamente uma vez; a rota começa e termina na base; só são usadas ruas que existem no grafo |
| **Saída** | A ordem de visita, o caminho completo vértice a vértice e a distância total |

### Da cidade aos pontos que importam

O algoritmo não precisa decidir esquina por esquina. Entre dois pontos consecutivos da ordem, o melhor trajeto é sempre o **menor caminho** no grafo. O problema então é resolvido em duas etapas:

1. **Pré-cálculo:** o algoritmo de **Dijkstra** roda a partir da base e de cada ponto de entrega. O resultado é uma tabela (k+1) × (k+1) com a menor distância entre cada par de pontos, mais os caminhos correspondentes.
2. **Busca:** o Simulated Annealing procura a melhor **ordem** consultando só essa tabela. No fim, cada trecho da ordem escolhida é trocado pelo seu caminho real nas ruas.

Assim a busca fica rápida, e a rota final usa apenas ruas que existem. Como o grafo é conexo, sempre existe uma rota válida.

### Instâncias de teste

As cidades são geradas sinteticamente:

1. parte-se de uma **grade n × n** de esquinas;
2. cada rua recebe uma distância inteira aleatória entre 1 e 10;
3. cerca de **30% das ruas são removidas**, mas uma rua só sai se a cidade continuar conexa;
4. a base e os k pontos de entrega são sorteados entre os vértices.

Tudo depende de uma **semente**. A mesma semente gera sempre a mesma cidade, o que permite reproduzir experimentos.

## 4. Simulated Annealing

### A ideia

O nome vem do **recozimento** na metalurgia. Um metal aquecido e resfriado devagar tem tempo de se organizar em uma estrutura estável, de baixa energia. No algoritmo:

- a **energia** é a distância total da rota;
- a **temperatura** T controla o quanto o algoritmo aceita **piorar** a solução temporariamente.

Aceitar pioras parece contraditório, mas é o que permite **escapar de mínimos locais**. Um mínimo local é uma rota que nenhuma pequena mudança melhora, embora exista uma rota bem melhor em outro lugar.

### Passo a passo

1. **Solução inicial:** usa a heurística do *vizinho mais próximo*. Partindo da base, o entregador vai sempre ao ponto não visitado mais próximo.
2. **Gerar um vizinho:** escolhe dois pontos da ordem e **inverte o trecho entre eles** (movimento *2-opt*). Por exemplo, `A B C D E` vira `A D C B E`. Esse movimento desfaz cruzamentos na rota.
3. **Decidir se aceita:** seja Δ a diferença de distância entre o vizinho e a solução atual.
   - Se Δ ≤ 0 (o vizinho é melhor ou igual), **aceita sempre**.
   - Se Δ > 0 (o vizinho é pior), **aceita com probabilidade e^(−Δ/T)**.
4. **Guardar a melhor:** a melhor rota já vista é sempre guardada.
5. **Resfriar:** multiplica a temperatura por α (por exemplo, 0,995): `T ← α · T`.
6. **Repetir** os passos 2 a 5 até atingir o número máximo de iterações ou até a temperatura ficar muito baixa (T < 0,001).

O passo 3 é o centro do algoritmo:

- com **T alta**, e^(−Δ/T) fica perto de 1, então quase toda piora é aceita e o algoritmo **explora** livremente;
- com **T baixa**, a probabilidade cai para perto de 0, só melhorias passam e o algoritmo **refina** a solução encontrada.

### Parâmetros

| Parâmetro | Efeito | Padrão |
| --- | --- | --- |
| Temperatura inicial T0 | Quanto maior, mais exploração no começo | 100 |
| Resfriamento α | Mais perto de 1 resfria mais devagar: mais iterações e, em geral, rotas melhores | 0,995 |
| Máximo de iterações | Limite de esforço computacional | 5000 |

### Como saber se a rota é boa?

O resultado do Simulated Annealing é comparado com duas referências:

- **Vizinho mais próximo:** a solução inicial. Mostra quanto o SA melhorou.
- **Força bruta:** testa todas as k! ordens e encontra o **ótimo exato**. Só é viável para k ≤ 8 e mostra quão longe o SA ficou do melhor possível (o *gap*).

## 5. A aplicação

A aplicação web permite ver o Simulated Annealing trabalhando, iteração por iteração.

### Instalação e execução

É preciso ter o [uv](https://docs.astral.sh/uv/) instalado.

```bash
uv sync                                    # instala as dependências
uv run streamlit run app/streamlit_app.py  # abre a aplicação no navegador
```

### Usando, passo a passo

1. **Monte a cidade** na barra lateral. Escolha a **semente**, o **tamanho da grade** e o **número de entregas k**.
2. **Ajuste o algoritmo:** temperatura inicial **T0**, resfriamento **α** e **máximo de iterações**.
3. Clique em **Executar**. Com *Animar a execução* marcado, o mapa mostra a rota mudando ao longo da busca.
4. **Leia o mapa:**
   - **B** (vermelho) é a base;
   - os pontos laranja são as entregas, numeradas na ordem de visita;
   - a linha **azul** é a melhor rota encontrada até aquela iteração;
   - a linha **cinza tracejada** é a rota corrente, que o algoritmo está explorando.
5. **Volte no tempo** com o slider *Iteração* para ver o estado da busca em qualquer momento.
6. **Acompanhe os gráficos:**
   - **Custo:** a distância da rota corrente oscila no começo (exploração) e se estabiliza no fim. A melhor distância só diminui.
   - **Temperatura:** decai de forma geométrica.
   - **Taxa de aceitação de pioras:** começa alta e cai junto com a temperatura. É a passagem da exploração para o refinamento.
7. **Compare** o resultado com o vizinho mais próximo e, para k ≤ 8, com o ótimo.
8. **Veja a resposta final:** a ordem de visita, o caminho completo vértice a vértice e a distância total.

### Sugestões de experimentos na aplicação

- **T0 muito baixa** (por exemplo, 0,1): o algoritmo quase não aceita pioras e tende a parar no primeiro mínimo local.
- **α = 0,9 contra α = 0,999:** resfriar rápido termina cedo; resfriar devagar costuma achar rotas mais curtas.
- **k pequeno (≤ 8):** confira se o SA chega ao ótimo da força bruta.
- **k grande (30 ou mais):** veja a diferença entre o SA e o vizinho mais próximo aumentar.

## 6. Experimentos em lote

O script abaixo roda o algoritmo em várias cidades, combinando valores de k, de α e de sementes:

```bash
uv run python experiments/run.py
```

Ele grava os resultados em `experiments/results/`:

- `results.csv`: uma linha por execução;
- `summary.csv`: médias por k e α;
- `improvement_over_nn.png`: melhoria sobre o vizinho mais próximo;
- `gap_to_optimum.png`: distância até o ótimo, para k ≤ 8.

Os valores testados ficam em constantes no início de `experiments/run.py`.

## 7. Organização do código

O fluxo dos dados segue a modelagem:

```
instance.py  →  distances.py  →  baselines.py  →  annealing.py  →  solution.py
  cidade         tabela de        solução          busca            rota final
  (grafo,        menores          inicial          pela melhor      (caminho
  base, W)       caminhos                          ordem            completo)
```

| Caminho | Conteúdo |
| --- | --- |
| `src/ktsp/instance.py` | Instância (grafo, base, W) e gerador de cidades sintéticas |
| `src/ktsp/distances.py` | Menores caminhos (Dijkstra) entre a base e os pontos de entrega |
| `src/ktsp/solution.py` | Custo de uma ordem e expansão no caminho completo |
| `src/ktsp/annealing.py` | Simulated Annealing (vizinho 2-opt e resfriamento geométrico) |
| `src/ktsp/baselines.py` | Vizinho mais próximo e força bruta |
| `app/streamlit_app.py` | Aplicação que mostra a busca |
| `experiments/run.py` | Experimentos em lote |
| `tests/` | Testes automatizados |

### Desenvolvimento

```bash
uv run pytest                                        # testes
uv run ruff check . && uv run ruff format --check .  # lint e formatação
```

A configuração do `ruff` e do `pytest` fica em `pyproject.toml`.

## Uso de IA Generativa

A aplicação foi desenvolvida com o **Claude Code**, um assistente de programação que roda no terminal. Ele lê o repositório, executa comandos e edita arquivos, sempre sob supervisão do desenvolvedor. Não houve uso de chats isolados: todo o trabalho com a IA aconteceu dentro do repositório. Os passos foram estes:

1. **Contexto do projeto.** O comando `/init` gerou o [`CLAUDE.md`](CLAUDE.md), que o assistente lê no início de cada sessão. Ele resume:
   - o problema;
   - a convenção de idioma (docstrings e interface em português, identificadores em inglês);
   - os comandos do projeto e a arquitetura dos módulos;
   - as boas práticas exigidas: estrutura coerente com a modelagem, SOLID, YAGNI e commits atômicos.
2. **Planejamento.** Antes de qualquer código, o assistente trabalhou em *modo de planejamento*. Ele propôs a modelagem (permutação de W com menores caminhos pré-calculados por Dijkstra), o algoritmo (2-opt com resfriamento geométrico) e a divisão em módulos. As decisões de projeto ficaram com o desenvolvedor, que escolheu:
   - **Streamlit** como interface, para manter tudo em Python;
   - um **gerador de cidades sintéticas** em vez de mapas reais;
   - o **uv** como gerenciador de pacotes, com o ambiente `.venv` já criado.
3. **Implementação.** Com o plano aprovado, o assistente:
   - criou o `pyproject.toml`;
   - adicionou as dependências com `uv add`;
   - escreveu os módulos de `src/ktsp/`, a aplicação em `app/` e o script de experimentos em `experiments/`.
4. **Verificação.** A cada etapa, o assistente rodou:
   - os testes automatizados (`pytest`), que conferem as restrições da rota e se o SA chega ao ótimo da força bruta em uma instância pequena;
   - o lint e a formatação (`ruff`);
   - a aplicação sem interface gráfica, pelo `AppTest` do Streamlit;
   - o script de experimentos.
5. **Documentação.** O assistente escreveu as docstrings e este README, seguindo a estrutura e o tom pedidos pelo desenvolvedor.

O desenvolvedor é o autor do projeto. A IA acelerou a escrita do código e da documentação, mas a modelagem, as escolhas de projeto e a aprovação de cada etapa ficaram com o desenvolvedor.
