# Travelling-Salesman-Problem

Planejamento da rota de um entregador de moto com **Simulated Annealing**. A rota precisa visitar um conjunto de pontos de entrega em uma cidade e voltar à base, percorrendo a menor distância possível.

Este README apresenta, em sequência:

1. o problema;
2. por que ele é difícil;
3. como ele foi modelado;
4. como o algoritmo o resolve;
5. como usar a aplicação que mostra o algoritmo funcionando;
6. como rodar pelo terminal e por que os resultados são reproduzíveis;
7. como rodar os experimentos em lote.

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

O TSP é **NP-difícil**: não se conhece algoritmo que encontre a melhor rota em tempo polinomial. A forma direta de resolvê-lo é testar todas as ordens possíveis, e o número de ordens cresce como k! (fatorial). Cada rota aparece em duas ordens, uma para cada sentido (as distâncias valem nos dois sentidos), então existem k!/2 rotas diferentes:

| Pontos (k) | Ordens possíveis (k!) | Rotas diferentes (k!/2) |
| ---: | ---: | ---: |
| 5 | 120 | 60 |
| 8 | 40 320 | 20 160 |
| 10 | 3 628 800 | 1 814 400 |
| 15 | ≈ 1,3 × 10¹² | ≈ 6,5 × 10¹¹ |
| 30 | ≈ 2,7 × 10³² | ≈ 1,3 × 10³² |

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

### Formulação matemática

Sejam G = (V, E) o grafo da cidade, com distância c_e em cada rua e, b a base e W o vetor com os k pontos de entrega. Os locais que importam formam o conjunto P = {b} ∪ W, com k + 1 elementos.

**Dados.** Para cada par de locais i, j em P, d_ij é a distância do **menor caminho** de i até j em G. É por meio de d_ij que o modelo trata o grafo não completo: dois pontos sem rua direta entre si continuam ligados, pelo caminho mais curto, que pode passar por quaisquer outras esquinas.

**Variáveis de decisão.** Para cada par de locais distintos i, j em P, x_ij vale 1 se a rota vai de i direto para j (pelo menor caminho) e 0 caso contrário. São (k + 1) · k variáveis.

**Função objetivo.** Minimizar a distância total:

  f(x) = Σ d_ij · x_ij, somada sobre todos os pares i ≠ j de P.

**Restrições.**

1. **Uma saída:** de cada local sai exatamente um trecho: Σ_j x_ij = 1 para todo i em P.
2. **Uma chegada:** a cada local chega exatamente um trecho: Σ_i x_ij = 1 para todo j em P.
3. **Uma volta só:** os trechos formam um único circuito que passa pela base, sem circuitos separados. Para todo subconjunto S de P, não vazio e diferente de P, pelo menos um trecho sai de S: Σ x_ij ≥ 1, com i em S e j fora de S.
4. **Domínio:** x_ij ∈ {0, 1}.

As restrições 1 e 2 garantem que cada ponto de W é visitado exatamente uma vez. As restrições 1 a 3 garantem que a rota começa e termina na base. A restrição de usar só ruas existentes é cumprida pela expansão de cada trecho no seu menor caminho em G.

**Representação da solução.** O algoritmo não manipula as variáveis x_ij diretamente. Ele guarda uma **permutação π** dos k pontos de W, e a rota é b → W[π₁] → … → W[πₖ] → b. Cada permutação corresponde a uma única escolha de x (x_ij = 1 exatamente para os pares consecutivos da rota) que cumpre as restrições 1 a 4. Assim, o algoritmo **nunca gera uma solução inválida**, e a função objetivo é calculada como f(π) = d(b, π₁) + Σ d(πᵢ, πᵢ₊₁) + d(πₖ, b).

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
6. **Repetir** os passos 2 a 5 até gastar o **orçamento**, o número de vizinhos avaliados. Toda execução gasta o orçamento inteiro, para que execuções com parâmetros diferentes sejam comparadas com o mesmo esforço.

O passo 3 é o centro do algoritmo:

- com **T alta**, e^(−Δ/T) fica perto de 1, então quase toda piora é aceita e o algoritmo **explora** livremente;
- com **T baixa**, a probabilidade cai para perto de 0, só melhorias passam e o algoritmo **refina** a solução encontrada.

### Parâmetros

| Parâmetro | Efeito | Padrão |
| --- | --- | --- |
| Temperatura inicial T0 | Quanto maior, mais exploração no começo | 100 |
| Resfriamento α | Mais perto de 1 resfria mais devagar e mantém a exploração por mais tempo | 0,995 |
| Orçamento (iterações) | Quantidade de vizinhos avaliados em cada execução | 5000 |

### Modo híbrido SA + Tabu (opcional)

O algoritmo do projeto é o Simulated Annealing. O modo híbrido existe só para comparação e fica desligado por padrão.

Quando a busca se aproxima de um ótimo local e a temperatura já está baixa, o SA passa a sortear repetidamente os mesmos vizinhos e rejeitá-los. Em execuções medidas, cerca de 85% dos vizinhos avaliados já tinham sido avaliados antes. O modo híbrido acrescenta uma **lista tabu** com os últimos movimentos 2-opt sorteados (os pares de posições invertidas):

- um movimento que está na lista **não é avaliado** e não gasta orçamento: outro é sorteado no lugar;
- todo movimento avaliado entra na lista e sai dela depois de L novos movimentos, em que L é o tamanho da lista;
- o restante do algoritmo (regra de aceitação, resfriamento, orçamento) é o mesmo do SA.

A lista guarda posições, não rotas: depois que um movimento é aceito, as mesmas posições passam a gerar outro vizinho. É uma simplificação comum da Tabu Search, que evita desfazer imediatamente um movimento e reavaliar o mesmo vizinho enquanto a solução atual não muda.

Na aplicação, o seletor **Modo de busca** escolhe entre *SA puro* e *SA + Tabu* e, no segundo caso, mostra o tamanho da lista. Para comparar, rode a mesma cidade com as mesmas sementes nos dois modos.

### Como saber se a rota é boa?

O resultado do Simulated Annealing é comparado com duas referências:

- **Vizinho mais próximo:** a solução inicial. Mostra quanto o SA melhorou.
- **Força bruta:** testa todas as k! ordens e encontra o **ótimo exato**. Só é viável para k ≤ 8 e mostra quão longe o SA ficou do melhor possível (o *gap*).

Para k > 8, os experimentos usam como referência a **melhor rota encontrada** em todas as execuções daquela cidade. Ela pode não ser o ótimo, e os resultados indicam qual referência foi usada (seção 7).

## 5. A aplicação

A aplicação web permite ver o Simulated Annealing trabalhando, iteração por iteração.

### Instalação e execução

É preciso ter o [uv](https://docs.astral.sh/uv/) e o Node.js instalados. O
solver continua em Python; a interface usa React e Vite.

```bash
uv sync
uv run python app/api.py
```

Em outro terminal:

```bash
cd web
npm install
npm run dev
```

Abra o endereço mostrado pelo Vite (normalmente `http://localhost:5173`). O Vite
encaminha as chamadas `/api` para a API Python em `http://127.0.0.1:8000`.

### Usando, passo a passo

1. **Monte a cidade** na barra lateral. Escolha a **semente da cidade**, a **semente do SA**, o **tamanho da grade** e o **número de entregas k**.
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
- **α = 0,9 contra α = 0,999:** com o mesmo orçamento, resfriar rápido vira busca local cedo; resfriar devagar explora por mais tempo e costuma achar rotas mais curtas.
- **k pequeno (≤ 8):** confira se o SA chega ao ótimo da força bruta.
- **k grande (30 ou mais):** veja a diferença entre o SA e o vizinho mais próximo aumentar.

## 6. Linha de comando e reprodutibilidade

### Resolver uma instância pelo terminal

```bash
uv run ktsp                                   # todos os parâmetros com o valor padrão
uv run ktsp --size 15 --k 8 --seed 7 --sa-seed 3 --t0 50 --alpha 0.999
uv run ktsp --help                            # lista os parâmetros e os padrões
```

| Parâmetro | Significado | Padrão |
| --- | --- | --- |
| `--size` | Lado da grade (a cidade tem size × size esquinas) | 12 |
| `--k` | Número de pontos de entrega | 10 |
| `--seed` | Semente da cidade: ruas, distâncias, base e entregas | 42 |
| `--sa-seed` | Semente das escolhas aleatórias do Simulated Annealing | 0 |
| `--t0` | Temperatura inicial | 100 |
| `--alpha` | Taxa de resfriamento | 0,995 |
| `--iterations` | Orçamento: vizinhos avaliados (a execução sempre gasta todos) | 5000 |
| `--tabu-tenure` | Tamanho da lista tabu do modo híbrido; 0 é o SA puro | 0 |

A saída mostra a distância do vizinho mais próximo, o ótimo (para k ≤ 8), a distância do SA, a ordem de visita e o caminho completo. A primeira linha é o comando completo, com todos os parâmetros, para repetir aquela execução.

### Por que os resultados são sempre os mesmos

Nenhum resultado depende de sorte ou da máquina. A mesma combinação de parâmetros produz sempre a mesma cidade, a mesma rota e a mesma distância:

- **Duas sementes explícitas.** A semente da cidade e a semente do SA são separadas. Assim dá para testar o SA com várias sementes na mesma cidade. As duas têm valor padrão fixo, e o programa não usa nenhuma outra fonte de aleatoriedade (relógio, sistema operacional, etc.).
- **Mesmo caminho em todas as interfaces.** A CLI e a API da aplicação web chamam a mesma função (`src/ktsp/pipeline.py`). Por isso os mesmos parâmetros dão o mesmo resultado no terminal e no navegador.
- **Versões fixas.** O gerador de números aleatórios do Python só garante a mesma sequência dentro da mesma versão do Python. Por isso o projeto exige o Python 3.12 (`.python-version` e `pyproject.toml`), e o `uv.lock` fixa a versão de cada biblioteca.
- **Teste de referência.** Um teste automatizado confere a cidade e a rota da execução padrão contra valores gravados. Se `uv run pytest` passa numa máquina, ela reproduz os mesmos resultados.

## 7. Experimentos em lote

O script abaixo roda o algoritmo em várias cidades, combinando valores de k e de α. Como o SA faz sorteios, um resultado isolado não diz muito: em cada combinação, o SA roda uma vez para cada semente do SA, e a análise olha a distribuição dos resultados. Todas as execuções gastam o mesmo orçamento, então a comparação entre valores de α é justa.

```bash
uv run python experiments/run.py                       # grade padrão
uv run python experiments/run.py --k 10 20 --alpha 0.99 0.999 --seeds 0 1 2 --sa-seeds 0 1 2 3 4
uv run python experiments/run.py --help                # lista os parâmetros
```

| Parâmetro | Significado | Padrão |
| --- | --- | --- |
| `--grid-size` | Lado da grade das cidades | 15 |
| `--k` | Valores de k testados | 6 8 15 30 |
| `--alpha` | Taxas de resfriamento testadas | 0,99 0,995 0,999 |
| `--seeds` | Sementes das cidades | 0 a 9 |
| `--sa-seeds` | Sementes do SA: uma execução por semente em cada cidade e α | 0 a 9 |
| `--t0` | Temperatura inicial | 100 |
| `--iterations` | Orçamento: vizinhos avaliados por execução | 20000 |
| `--output` | Pasta onde cada execução cria a sua subpasta | `experiments/results/` |

Cada execução cria uma pasta nova dentro de `--output`, no formato `<timestamp>-<commit>` (com `-dirty` no fim quando há alterações não commitadas), por exemplo `20261029T055508Z-70fc5c5`. O timestamp é o horário de início em UTC (o `Z` no fim), e o commit são os 7 primeiros caracteres do commit do código. Assim nenhuma execução sobrescreve outra, e cada resultado mostra no nome de qual versão do código veio. Se o código tiver alterações não commitadas, o nome ganha o sufixo `-dirty` (por exemplo, `20261029T055508Z-70fc5c5-dirty`): esse resultado não pode ser reproduzido só com o commit, e o mesmo fica registrado no `params.json`.

Cada pasta contém:

- `params.json`: os parâmetros usados, o commit do código (e se havia alterações não commitadas) e as versões do Python e das bibliotecas, para repetir e rastrear o experimento;
- `results.csv`: uma linha por execução (resultado bruto);
- `summary.csv`: métricas por k e α (resultado derivado);
- `deviation.png`, `hit_rate.png` e `improvement_over_nn.png`: as métricas abaixo, por k e α.

| Métrica | O que responde | Como se calcula |
| --- | --- | --- |
| Desvio (%) | Quão longe da melhor rota conhecida? | 100 × (distância − referência) ÷ referência |
| Taxa de acerto (%) | Quantas execuções chegam à melhor rota conhecida? | 100 × acertos ÷ execuções |
| Melhoria sobre o vizinho mais próximo (%) | Quanto o SA encurtou a solução inicial? | 100 × (inicial − SA) ÷ inicial |
| Avaliações até a melhor (`found_at`) | Quanto do orçamento o SA precisou? | Iteração em que a melhor rota da execução apareceu |
| Tempo (`seconds`) | Quanto custa cada execução? | Relógio do início ao fim |

A **referência** é o ótimo exato quando k ≤ 8 e, para k maior, a melhor rota achada em todas as execuções daquela cidade. A coluna `reference_is_optimum` diz qual das duas foi usada, porque a segunda pode não ser o ótimo.

Todas as colunas se repetem em qualquer máquina, exceto `seconds`, que mede o tempo de execução.

## 8. Organização do código

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
| `src/ktsp/pipeline.py` | Execução completa (cidade + SA) a partir das sementes, usada pela CLI e pela API |
| `src/ktsp/cli.py` | Linha de comando `ktsp` |
| `app/api.py` | API local que executa o solver Python e entrega os dados à interface |
| `web/` | Interface React com Vite, mapa, reprodução e gráficos |
| `experiments/run.py` | Experimentos em lote |
| `tests/` | Testes automatizados |

### Desenvolvimento

```bash
uv run pytest                                        # testes
uv run ruff check . && uv run ruff format --check .  # lint e formatação
```

A configuração do `ruff` e do `pytest` fica em `pyproject.toml`.

## Problemas conhecidos

### Windows: `ImportError: DLL load failed while importing mtrand`

O script de experimentos (`uv run python experiments/run.py`) para com o erro:

```
ImportError: DLL load failed while importing mtrand:
Uma política de Controlo de Aplicações bloqueou este ficheiro.
```

**Causa:** o **Smart App Control** do Windows 11 bloqueia uma DLL do NumPy (`numpy\random\mtrand.*.pyd`). O NumPy é usado pelo pandas e pelo matplotlib no script de experimentos. A API e a interface React não usam o NumPy. Não é um defeito do projeto.

**Solução:**

1. Abra **Segurança do Windows → Controlo de aplicações e browser → Definições do Smart App Control**.
2. Mude a opção para **Desativado**.
3. Rode de novo `uv run python experiments/run.py`. Não é preciso reinstalar nada.

> Em algumas versões do Windows 11, depois de desligado, o Smart App Control só volta a ser ligado reinstalando o sistema.

Em computadores gerenciados (por exemplo, de empresas), o bloqueio pode vir de uma política do administrador, que o usuário não consegue desativar. Nesse caso, peça a liberação ao administrador ou rode o projeto no **WSL** (Ubuntu dentro do Windows), onde os mesmos comandos `uv` funcionam.

## Uso de IA Generativa

A aplicação foi desenvolvida com o **Claude Code**, um assistente de programação que roda no terminal. Ele lê o repositório, executa comandos e edita arquivos, sempre sob supervisão do desenvolvedor. Não houve uso de chats isolados: todo o trabalho com a IA aconteceu dentro do repositório. Os passos foram estes:

1. **Contexto do projeto.** O comando `/init` gerou o [`CLAUDE.md`](CLAUDE.md), que o assistente lê no início de cada sessão. Ele resume:
   - o problema;
   - a convenção de idioma (docstrings e interface em português, identificadores em inglês);
   - os comandos do projeto e a arquitetura dos módulos;
   - as boas práticas exigidas: estrutura coerente com a modelagem, SOLID, YAGNI e commits atômicos.
2. **Planejamento.** Antes de qualquer código, o assistente trabalhou em *modo de planejamento*. Ele propôs a modelagem (permutação de W com menores caminhos pré-calculados por Dijkstra), o algoritmo (2-opt com resfriamento geométrico) e a divisão em módulos. As decisões de projeto ficaram com o desenvolvedor, que escolheu:
   - **React com Vite** como interface e uma API Python local para manter o solver;
   - um **gerador de cidades sintéticas** em vez de mapas reais;
   - o **uv** como gerenciador de pacotes, com o ambiente `.venv` já criado.
3. **Implementação.** Com o plano aprovado, o assistente:
   - criou o `pyproject.toml`;
   - adicionou as dependências com `uv add`;
   - escreveu os módulos de `src/ktsp/`, a aplicação em `app/` e o script de experimentos em `experiments/`.
4. **Verificação.** A cada etapa, o assistente rodou:
   - os testes automatizados (`pytest`), que conferem as restrições da rota e se o SA chega ao ótimo da força bruta em uma instância pequena;
   - o lint e a formatação (`ruff`);
   - a interface React e a API local;
   - o script de experimentos.
5. **Documentação.** O assistente escreveu as docstrings e este README, seguindo a estrutura e o tom pedidos pelo desenvolvedor.

O desenvolvedor é o autor do projeto. A IA acelerou a escrita do código e da documentação, mas a modelagem, as escolhas de projeto e a aprovação de cada etapa ficaram com o desenvolvedor.
