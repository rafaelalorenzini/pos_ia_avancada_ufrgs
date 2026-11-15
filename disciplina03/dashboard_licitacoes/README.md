# Prova final · Amostragem e inferência nas licitações do RS

Dashboard da prova final da disciplina 03: amostragem aleatória simples, intervalos de confiança e testes de
hipóteses sobre as licitações e contratos do TCE-RS (2025–2026). O enunciado e os critérios de avaliação estão em
[`enunciado.md`](enunciado.md).

## Como rodar

```bash
cd disciplina03/dashboard_licitacoes
uv sync
uv run python preparar_dados.py     # monta data/populacao.parquet, amostra.parquet, municipios.parquet e metadados.json
uv run streamlit run app.py         # abre o dashboard em http://localhost:8501
uv run python testes.py             # opcional: fórmulas, resultados da amostra oficial e todas as páginas sem navegador
```

`preparar_dados.py` lê os zips do TCE-RS em `disciplina03/data/raw/` (os mesmos do notebook; também estão na
[Release `dados-brutos`](https://github.com/rafaelalorenzini/pos_ia_avancada_ufrgs/releases/tag/dados-brutos)) e baixa do IBGE a
lista de municípios do RS, a malha municipal e a população do Censo 2022 (`data/ibge/`).

| Arquivo | Conteúdo |
|---|---|
| `preparar_dados.py` | Uma linha por licitação; modalidade, valores, competição, contratos, objeto, natureza, datas, prazos e município (IBGE); dimensiona e sorteia a AAS |
| `estatistica.py` | Tamanho da amostra, AAS, IC, testes z e t, bootstrap, simulação e aderência (qui-quadrado e KS) |
| `comum.py` | Carga dos dados, formatação pt-BR, dicionários de variáveis, CSS e componentes de texto |
| `graficos.py` | Template Plotly único (paleta validada para daltonismo) e todas as funções de gráfico |
| `app.py` | Navegação e barra lateral (amostra oficial ou personalizada) |
| `paginas/` | `base.py`, `populacao.py` (Painel 1), `amostra.py` (Painel 2), `inferencia.py` (Painel 3), `descritiva.py` (seções comuns aos Painéis 1 e 2) |
| `testes.py` | Checagens de fórmulas e de páginas com `AppTest` |
| `gerar_roteiro_pdf.py` | Gera `roteiro_video.pdf` (fala do vídeo por bloco, tempos, checklist dos critérios, como gravar) |

## O que o dashboard mostra

- **Base e amostragem:** fluxograma de como a população foi montada, gráfico de cobertura das variáveis, fórmula do n
  com os números substituídos, gráfico n × margem de erro, gráfico de uniformidade do sorteio e download da amostra.
- **Painel 1 (população)** em 7 seções com leitura interpretativa em cada gráfico: perfil (modalidade, treemap
  modalidade → objeto, heatmap modalidade × tipo de órgão), série mensal, **mapas do RS** (habitantes, licitações por
  1.000 hab., total, % dispensa), dispersão licitações × habitantes, valores (log-normal, boxplot por modalidade, curva
  de concentração), competição e prazo, contratos e aditivos, explorador de variáveis e tabela de medidas.
- **Painel 2 (amostra):** as mesmas seções sobrepondo população e amostra, mais a seção "A amostra representa a
  população?" com a diferença em p.p. de cada categoria (com a faixa de ±1,96 EP) e os testes de aderência.
- **Painel 3 (inferência):** uma aba por hipótese com fórmula e números substituídos, condições, IC de Wilson ou
  bootstrap como checagem, a distribuição da estatística sob H₀ com a região crítica, IC × parâmetro e a conclusão.
  Depois vêm um resumo gráfico das quatro hipóteses, a simulação de variabilidade e as limitações.
- **Roteiro do vídeo:** fora do app, no PDF [`roteiro_video.pdf`](roteiro_video.pdf), gerado por `uv run --with reportlab python gerar_roteiro_pdf.py`.

## Desenho do estudo

- **Fonte:** LicitaCon/TCE-RS: [licitações 2025](https://dados.tce.rs.gov.br/dataset/licitacoes-consolidado-2025),
  [licitações 2026](https://dados.tce.rs.gov.br/dataset/licitacoes-consolidado-2026),
  [contratos 2025](https://dados.tce.rs.gov.br/dataset/contratos-consolidado-2025),
  [contratos 2026](https://dados.tce.rs.gov.br/dataset/contratos-consolidado-2026). Municípios e população: IBGE.
- **População:** 305.062 licitações (inclui dispensas e inexigibilidades) com ano 2025 ou 2026.
- **Unidade amostral:** a licitação (órgão + número + ano + modalidade).
- **Tamanho da amostra:** proporção em população finita (fórmula da calculadora USP/Bauru), 95%, E = 2%, p = 0,5 →
  **n = 2.383**.
- **AAS:** `numpy.random.default_rng(20261110).choice(N, n, replace=False)` sobre a população em ordem fixa.

| | Pergunta | H₀ × H₁ | Amostra | IC 95% | Valor-p | Decisão | População |
|---|---|---|---|---|---|---|---|
| P1 | Maioria é dispensa? | p ≤ 50% × p > 50% | 54,64% | [52,64% ; 56,64%] | 3,0e-06 | Rejeita H₀ | 55,88% |
| P2 | Menos da metade gera contrato? | p ≥ 50% × p < 50% | 41,08% | [39,11% ; 43,06%] | 1,6e-18 | Rejeita H₀ | 41,13% |
| M1 | Mais de 3 licitantes em pregão/concorrência? | μ ≤ 3 × μ > 3 | 8,70 | [7,48 ; 9,93] | 1,0e-18 | Rejeita H₀ | 8,10 |
| M2 | Desconto médio de 20%? | μ = 20 × μ ≠ 20 | 22,31% | [19,48 ; 25,13] | 0,109 | Não rejeita H₀ | 23,38% |

Os rótulos de `TP_OBJETO` (Compras, Outros serviços, Compras e serviços, Obras e serviços de engenharia) foram conferidos
lendo as descrições dos objetos de cada código, porque o manual do leiaute do LicitaCon estava fora do ar no download.
