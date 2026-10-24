# 01 · Solver simples para o ARC-AGI

Um solver mínimo e didático, em dois arquivos:

- [`solver/main.py`](solver/main.py) mostra ao modelo os exemplos de treino e a entrada de teste,
  pede a regra e a grade de saída, e salva o resultado;
- [`solver/validator.py`](solver/validator.py) compara a resposta com a saída esperada, célula a
  célula.

O modelo padrão é o **Gemma 4 31B** com raciocínio alto, pela API do Google ou pelo OpenRouter.

## Como rodar

A partir desta pasta (as chaves ficam no `.env` de `disciplina02/`):

```bash
uv run solver/main.py ../data/training/007bbfb7.json
uv run solver/main.py ../data/training/007bbfb7.json --provider openrouter
uv run solver/main.py ../data/training/44f52bb0.json --model gemini-flash-lite
```

Cada execução cria `outputs/<tarefa>_<data_hora>/` com:

| Arquivo | Conteúdo |
|---|---|
| `prompt.txt` | o prompt enviado ao modelo |
| `log.txt` | provedor, modelo, tempo, tokens e a resposta bruta |
| `answer.json` | o resumo da regra e as grades previstas |
| `reasoning.txt` | quantos tokens de raciocínio o modelo usou |

Para validar uma resposta:

```bash
uv run solver/validator.py ../data/training/007bbfb7.json outputs/007bbfb7_20261021_222026/answer.json
```

## Resultados

| Tarefa | Modelo | Tokens (entrada / raciocínio / saída) | Resultado |
|---|---|---|---|
| 007bbfb7 | Gemma 4 31B | 1.111 / 5.889 / 351 | ✅ 1/1 |
| 44d8ac46 | Gemma 4 31B | 2.773 / 7.575 / 486 | ✅ 1/1 |
| 44f52bb0 | Gemini 3.5 Flash Lite | 367 / 5.664 / 67 | ✅ 2/2 |
