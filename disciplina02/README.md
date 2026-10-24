# IA002 · Explorando o Potencial de Agentes de IA Generativa

Disciplina sobre o uso de **agentes de codificação** (como o Claude Code) e de **LLMs** para
resolver problemas de raciocínio. O fio condutor é o [ARC-AGI-1](https://arcprize.org/arc-agi/1):
cada tarefa mostra alguns pares de grades de entrada e saída, e o solver precisa inferir a regra
e produzir a grade de saída para uma entrada nova. A resposta só conta quando a grade inteira
está certa.

Todos os solvers desta pasta foram construídos com a ajuda de um agente de codificação.

## Conteúdo

| Pasta | O que é | Modelo | Resultado |
|---|---|---|---|
| [`01_solver_simples/`](01_solver_simples/) | Primeiro solver: um arquivo que resolve uma tarefa e outro que valida a resposta | Gemma 4 31B (e Gemini 3.5 Flash Lite) | 3 tarefas testadas, 3 resolvidas |
| [`02_arc_solver/`](02_arc_solver/) | Solver modular que roda uma lista de tarefas e gera um resumo do experimento | Gemini 3.5 Flash Lite | 2/5 no experimento *baseline* |
| [`03_prova_final/`](03_prova_final/) | **Projeto final (nível 2):** fim a fim × geração de código em 20 tarefas, com relatório IJCAI | Gemini 3.5 Flash Lite | **17/20** fim a fim · **18/20** geração de código |
| [`data/`](data/) | As 800 tarefas do ARC-AGI-1 (400 de treino e 400 de avaliação) | — | — |

## Resultado do projeto final

| Abordagem | Resolvidas | Tokens de entrada | Tokens de raciocínio | Tokens de saída | Tempo |
|---|---|---|---|---|---|
| Fim a fim | 17/20 | 37.276 | 198.615 | 5.903 | 570 s |
| Geração de código | **18/20** | 37.976 | 202.445 | 7.284 | 611 s |

A geração de código resolveu uma tarefa a mais, com custo semelhante, e o acerto no treino se
mostrou um bom sinal de acerto no teste. Os detalhes estão no
[relatório](03_prova_final/relatorio/relatorio.pdf).

## Configuração

1. Instale o [uv](https://docs.astral.sh/uv/): `pip install uv`.
2. Copie `.env.example` para `.env` nesta pasta e preencha as chaves. A chave do Google é
   gratuita e pode ser criada no [Google AI Studio](https://aistudio.google.com/api-keys).
3. Entre na pasta do trabalho e siga o README dela. O `uv run` cria o ambiente sozinho na
   primeira execução.

Os solvers procuram o `.env` na própria pasta e nas pastas acima, então um único `.env` aqui
serve para todos.

## Dados

As tarefas em `data/` vêm do repositório [fchollet/ARC-AGI](https://github.com/fchollet/ARC-AGI)
(licença Apache 2.0). As 20 tarefas do projeto final estão em `03_prova_final/tarefas/`.
