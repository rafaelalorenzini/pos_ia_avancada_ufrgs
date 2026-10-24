# Solver ARC-AGI-1: fim a fim × geração de código

Resolve as 20 tarefas de `tarefas/tarefas.txt` com o Gemini 3.5 Flash Lite (`gemini-3.5-flash-lite`,
API do Google, raciocínio **alto**) de duas formas:

- **Fim a fim** (`direct`): o modelo recebe os exemplos e escreve as grades de saída do teste em JSON.
- **Geração de código** (`code`): o modelo escreve uma função Python `transform(grid)`. O solver a executa
  em um processo separado, com tempo limite de 10 s, em cada exemplo de treino e na(s) entrada(s) de teste.

## Instalação

O projeto usa o [uv](https://docs.astral.sh/uv/). Se ele não estiver instalado:

```bash
pip install uv
```

Não é preciso criar ambiente nem instalar dependências: o `uv run` faz isso sozinho na primeira vez,
a partir do `pyproject.toml` e do `uv.lock` da pasta do projeto.

Coloque a chave no arquivo `.env` da pasta do projeto (nunca no código):

```
GOOGLE_API_KEY=...
```

Extraia o `tarefas.zip` na pasta do projeto. A estrutura esperada é:

```
pasta_do_projeto/
  .env
  pyproject.toml
  uv.lock
  solver/
  tarefas/tarefas.txt, tarefas/training/, tarefas/evaluation/
  resultados/
```

## Como rodar

A partir da pasta do projeto (a que contém `solver/` e `tarefas/`):

```bash
uv run solver/main.py                                    # 20 tarefas, as duas abordagens
uv run solver/main.py --approach direct                  # só fim a fim
uv run solver/main.py --approach code                    # só geração de código
uv run solver/main.py tarefas/training/0a938d79.json     # uma tarefa
uv run solver/main.py --only 3aa6fb7a 44d8ac46           # algumas tarefas da lista
uv run solver/main.py --model gemini-3.5-flash-lite --reasoning high --label final
```

| Opção | Padrão | Valores |
|---|---|---|
| `--approach` | `both` | `both`, `direct`, `code` |
| `--model` | `gemini-3.5-flash-lite` | qualquer modelo da API escolhida |
| `--reasoning` | `high` | `minimal`, `low`, `medium`, `high` |
| `--provider` | `google` | `google`, `openrouter` |
| `--label` | `experiment` | nome do experimento (prefixo da pasta de resultados) |

Há uma pausa de 2 s entre uma tarefa e outra, e erros temporários da API (429/5xx) são repetidos.

## Saída

Tudo é salvo em `resultados/<label>_<data_hora>/`:

| Arquivo | Conteúdo |
|---|---|
| `summary_direct.json` / `.csv` | fim a fim: resolvidas (de 20), total de tokens de entrada/raciocínio/saída, tempo total e o resultado de cada tarefa |
| `summary_code.json` / `.csv` | geração de código: o mesmo, mais em quantas tarefas o programa acertou **todos** os exemplos de treino |
| `<abordagem>/<task_id>/` | o prompt, a resposta bruta, `answer.json` e, na geração de código, `transform.py` |

Na entrega, a pasta `resultados/` traz o resumo fim a fim de
`uv run solver/main.py --label completo` e o resumo da geração de código de
`uv run solver/main.py --approach code --label geracao_codigo`.

O tempo de cada tarefa inclui a chamada à API e, na geração de código, a execução do programa.
`total_seconds` soma o tempo das tarefas; `wall_clock_seconds` inclui também as pausas.

Para inspecionar uma resposta célula por célula:

```bash
uv run solver/validator.py tarefas/training/3aa6fb7a.json resultados/<run>/direct/3aa6fb7a/answer.json
```

## Arquivos

| Arquivo | Função |
|---|---|
| `main.py` | ponto de entrada: lê a lista de tarefas, roda cada abordagem e salva os resumos |
| `llm.py` | chama o modelo (API do Google, ou OpenRouter com `--provider openrouter`) e conta os tokens |
| `prompt.py` | monta os dois prompts e lê as respostas (grades em JSON ou o código de `transform`) |
| `sandbox.py` | executa `transform(grid)` em um processo filho com tempo limite |
| `validator.py` | compara as grades previstas com as esperadas |
