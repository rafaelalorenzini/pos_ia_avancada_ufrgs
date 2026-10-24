# 03 · Projeto final: resolvendo o ARC-AGI-1 com LLMs (nível 2)

Solver em Python que resolve **20 tarefas do ARC-AGI-1** com o **Gemini 3.5 Flash Lite**
(raciocínio alto) de duas formas, e compara acerto, tokens e tempo:

- **Fim a fim:** o modelo recebe os exemplos e escreve a grade de saída diretamente.
- **Geração de código:** o modelo escreve uma função `transform(grid)` em Python, e o solver a
  executa, com tempo limite, nos exemplos de treino e na entrada de teste.

O solver foi construído com o agente de codificação **Claude Code**. O enunciado completo está em
[`enunciado/projeto.pdf`](enunciado/projeto.pdf).

## Resultados

| Abordagem | Resolvidas | Entrada | Raciocínio | Saída | Tempo |
|---|---|---|---|---|---|
| Fim a fim | 17/20 | 37.276 | 198.615 | 5.903 | 570,0 s |
| Geração de código | **18/20** | 37.976 | 202.445 | 7.284 | 611,2 s |

- Na geração de código, o programa acertou todos os exemplos de treino em **18 tarefas**, e
  todas elas também acertaram o teste.
- As abordagens erram tarefas diferentes: a fim a fim errou c658a4bd, d47aa2ff e f5aa3634; a
  geração de código errou 32597951 e f5aa3634. Juntas, cobririam 19 das 20 tarefas.

📄 Relatório (template IJCAI, 2 páginas): [`relatorio/relatorio.pdf`](relatorio/relatorio.pdf)

## Estrutura

```
03_prova_final/
├── enunciado/      projeto.pdf, tarefas.zip e template.zip, como foram fornecidos
├── solver/         código do solver (veja solver/README.md)
├── tarefas/        as 20 tarefas e a lista tarefas.txt
├── resultados/     uma pasta por rodada, com o resumo de cada abordagem
├── relatorio/      relatorio.tex, relatorio.pdf e os arquivos do template IJCAI
├── entrega/        rafaela_lorenzini.zip, o arquivo enviado no Moodle
├── pyproject.toml
└── uv.lock
```

### Rodadas em `resultados/`

| Pasta | Comando | Uso |
|---|---|---|
| `completo_20261024_093737/` | `uv run solver/main.py --label completo` | **fim a fim do relatório** (17/20) |
| `geracao_codigo_20261024_095945/` | `uv run solver/main.py --approach code --label geracao_codigo` | **geração de código do relatório** (18/20), com NumPy e SciPy liberados |
| `fim_a_fim_20261024_092102/` | `uv run solver/main.py --approach direct --label fim_a_fim` | outra rodada fim a fim (17/20), citada como variação entre execuções |

A geração de código de `completo_*` (14/20) é anterior à inclusão do SciPy: três programas
falharam porque o SciPy não estava instalado. Por isso a rodada `geracao_codigo_*` foi feita.

## Como rodar

A partir desta pasta, com a chave no `.env` (aqui ou em `disciplina02/`):

```bash
uv run solver/main.py                                     # 20 tarefas, as duas abordagens
uv run solver/main.py --approach code                     # só geração de código
uv run solver/main.py tarefas/training/0a938d79.json --model gemini-3.5-flash-lite --reasoning high
```

Todas as opções e os arquivos de saída estão descritos em [`solver/README.md`](solver/README.md).
