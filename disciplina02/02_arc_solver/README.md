# 02 · ARC solver com experimentos

Uma evolução do [solver simples](../01_solver_simples/): o código foi dividido em módulos, e o
solver passou a rodar uma **lista de tarefas** e a gerar um resumo do experimento
(`summary.json`). Usa o **Gemini 3.5 Flash Lite** com raciocínio alto.

| Arquivo | Função |
|---|---|
| [`main.py`](main.py) | ponto de entrada: acha as tarefas, resolve cada uma e salva o resumo |
| [`prompt.py`](prompt.py) | monta o prompt e lê o resumo da regra e as grades da resposta |
| [`llm.py`](llm.py) | chama o modelo (Google ou OpenRouter) e conta os tokens |
| [`validator.py`](validator.py) | confere as grades e mostra a diferença célula a célula |
| [`tasks.txt`](tasks.txt) | a lista de tarefas do experimento |

## Como rodar

A partir desta pasta (as chaves ficam no `.env` de `disciplina02/`):

```bash
uv run main.py 007bbfb7                          # uma tarefa, pelo id (procura em ../data)
uv run main.py ../data/training/007bbfb7.json    # uma tarefa, pelo caminho
uv run main.py tasks.txt --label baseline        # várias tarefas + summary.json
uv run main.py tasks.txt --provider openrouter
```

Os resultados vão para `results/<label>_<data_hora>/`.

## Resultados

Experimento *baseline* ([`results/baseline_20261021_225004/`](results/baseline_20261021_225004/)):
**2 de 5 tarefas resolvidas**.

| Tarefa | Resultado |
|---|---|
| 007bbfb7 | ✅ |
| 00d62c1b | ❌ |
| 017c7c7b | ✅ |
| 025d127b | ❌ |
| 045e512c | ❌ |

Total de tokens: 13.015 de entrada, 61.652 de raciocínio e 3.583 de saída.
