# Pós-graduação em Inteligência Artificial Avançada

Repositório com os trabalhos, experimentos e projetos que desenvolvi na **Especialização em
Inteligência Artificial Avançada (UFRGS)**.

Cada disciplina tem a sua pasta, com um README próprio que explica o conteúdo, os resultados e
como rodar o código.

## Disciplinas

| Pasta | Disciplina | Destaques |
|---|---|---|
| [`disciplina02/`](disciplina02/) | **IA002 · Explorando o Potencial de Agentes de IA Generativa** | Solvers para o benchmark [ARC-AGI-1](https://arcprize.org/arc-agi/1) com LLMs (Gemma 4 31B e Gemini 3.5 Flash Lite), construídos com um agente de codificação. Projeto final: fim a fim × geração de código. |

## Como usar

Os projetos em Python usam o [uv](https://docs.astral.sh/uv/) para gerenciar o ambiente e as
dependências:

```bash
pip install uv
```

As chaves de API ficam em arquivos `.env`, que **não** são versionados. Cada disciplina que
precisa de chaves traz um `.env.example` com o formato esperado.

---

Rafaela Lorenzini
