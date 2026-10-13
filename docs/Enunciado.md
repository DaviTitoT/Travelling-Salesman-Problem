# Projeto Prático: Problemas Intratáveis

## 1. Visão Geral

O Projeto Prático tem como propósito aplicar, a um problema realista, os conteúdos de intratabilidade da disciplina. Cada grupo escolhe um tema, que combina um problema de otimização NP-difícil com um algoritmo conhecido, e implementa esse algoritmo em Python para resolver o problema.

Espera-se que cada grupo modele o problema, com variáveis, objetivos e restrições, implemente o algoritmo indicado no tema, gere as próprias instâncias de teste, avalie os resultados com experimentos e organize o código com boas práticas de desenvolvimento. Assim, o projeto leva para a prática as noções de problemas intratáveis, de heurísticas e metaheurísticas e de formulações mono-objetivo e multi-objetivo.

## 2. Organização

- Linguagem: Python é obrigatório. O uso de outra linguagem numa parte específica do projeto, como um front-end, depende de aprovação prévia e explícita do professor.

- Instâncias: o próprio grupo é responsável por gerar as instâncias (entradas) usadas nos testes e nos experimentos.

- Uso de Inteligência Artificial Generativa: permitido, mas não obrigatório. Quem usar deve declarar o uso (explicando-o na apresentação) e passa a ser avaliado no item de IA Generativa da Seção 3. Quem não usar não precisa declarar e não é avaliado neste item. O grupo é o detentor da autoria do trabalho, por isso deve ter pleno entendimento dos artefatos produzidos e do seu tema.

A entrega final é avaliada pelos critérios da tabela abaixo.

| Critério | Tipo | Peso | Descrição |
| --- | --- | --- | --- |
| Modelagem do problema | Grupo | 100% | Formulação correta e clara do problema do tema, com variáveis, objetivos, restrições, representação da solução e as instâncias geradas pelo grupo. |
| Algoritmo e análise de resultados | Grupo | 15% | Implementação correta do algoritmo do tema (incluindo a abordagem multi-objetivo quando houver), com as escolhas de projeto justificadas. Experimentos com as instâncias geradas, resultados em gráficos e tabelas e uma análise que separa os resultados das interpretações. |
| Domínio do problema e dos artefatos | Individual | 50% | Entendimento de cada integrante sobre o problema, o algoritmo, o código e os resultados avaliado na apresentação e na arguição. |
| Boas práticas de desenvolvimento e organização do repositório | Grupo | 25% | Atendimento às práticas de desenvolvimento listadas na Seção 3. |

## 3. Boas práticas de desenvolvimento

O critério "Boas práticas de desenvolvimento e organização do repositório", presente na apresentação final, avalia os itens abaixo:

- Estrutura de pacotes e módulos coerente com a modelagem do problema.

- Nomes claros e consistentes.

- Documentação do código (docstrings, comentários e README.md).

- Uso de controle de versão (GitHub), com commits atômicos e mensagens de commit claras.

- Uso de ferramentas de análise estática de código (linters, formatadores etc.), configuradas de forma explícita no repositório do grupo.

- Uso de boas práticas de programação (princípios SOLID e YAGNI).

- IA Generativa (somente para quem usar): o uso apenas de chats é fortemente desestimulado, e o uso de harnesses agênticos (por exemplo, OpenCode, Codex, Cursor e Claude Code) é extremamente recomendado. O repositório deve indicar os arquivos de configuração (por exemplo, CLAUDE.md, AGENTS.md, rules e hooks) que descrevem como a IA Generativa foi instruída no projeto.

## 4. Tema

### Turno de um entregador de moto

- Visão Geral: A cidade é representada por um grafo. Os vértices são esquinas e pontos de entrega, e as arestas são ruas com as suas distâncias. No início do turno, o usuário (entregador de moto) recebe da central os pontos de entrega do turno e precisa visitá-los todos, saindo da base e voltando a ela. A equipe de desenvolvimento (grupo do trabalho) recebe o grafo, o vértice da base e um vetor W, de tamanho k, com exatamente os pontos a visitar. A moto pode passar por qualquer vértice no caminho. A equipe decide a ordem de visita dos pontos de W e o caminho mais curto entre cada par de pontos consecutivos. Ela entrega a ordem, o caminho completo vértice a vértice e a distância total.

- Problema: Traveling Salesman Problem (TSP) — k-TSP. O veículo visita exatamente os k pontos de um vetor W dado. O grafo não liga todos os pares de pontos, e o caminho entre dois pontos de W pode passar por outros vértices.

- Categoria: Mono-Objetivo

- Objetivo: Minimizar a distância total percorrida.

- Restrições: Cada ponto de W aparece exatamente uma vez na ordem de visita. A rota começa e termina na base. A rota usa só arestas que existem no grafo. O grafo é conexo, então sempre existe uma rota válida.

- Algoritmo: Simulated Annealing (SA)

## 5. Proposta de Aplicação

TODO
