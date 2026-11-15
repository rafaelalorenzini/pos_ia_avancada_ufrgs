import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import graficos as g
from comum import QUALI, QUANTI, contexto, fmt_num, fmt_pct, fmt_rs, hero, leitura, secao
from estatistica import tamanho_amostra

ctx = contexto()
pop, amo, meta, dim = ctx["pop"], ctx["amostra"], ctx["meta"], ctx["dim"]
N = len(pop)

hero("Prova final · Disciplina 03 · Especialização em IA Avançada (UFRGS)",
     "Licitações e contratos no RS: amostragem e inferência",
     "Compras públicas de 2025 e 2026 registradas no LicitaCon (TCE-RS). Uma população de 305 mil licitações, uma amostra "
     "aleatória simples e quatro hipóteses para ver o quanto a amostra consegue dizer sobre o todo.")

secao("01", "A base de dados", "Fonte, contexto, tamanho, população de interesse e unidade amostral.")
k = st.columns(5)
k[0].metric("Observações (licitações)", fmt_num(N, 0), border=True)
k[1].metric("Variáveis analisadas", f"{len(QUALI) + len(QUANTI)}", "de 66 + 28 colunas brutas", delta_color="off", border=True)
k[2].metric("Órgãos", fmt_num(pop["CD_ORGAO"].nunique(), 0), border=True)
k[3].metric("Contratos ligados", fmt_num(meta["n_registros_contratos"], 0), border=True)
k[4].metric("Valor de referência total", fmt_rs(pop["VL_REF"].sum()), border=True)

c1, c2 = st.columns(2, gap="medium")
with c1, st.container(border=True):
    st.markdown(f"""
**Fonte:** Tribunal de Contas do Estado do RS (TCE-RS), Portal de Dados Abertos, sistema **LicitaCon**
(dados baixados em {meta['data_download']}).

- Licitações: [licitacoes-consolidado-2025](https://dados.tce.rs.gov.br/dataset/licitacoes-consolidado-2025) ·
  [licitacoes-consolidado-2026](https://dados.tce.rs.gov.br/dataset/licitacoes-consolidado-2026)
- Contratos: [contratos-consolidado-2025](https://dados.tce.rs.gov.br/dataset/contratos-consolidado-2025) ·
  [contratos-consolidado-2026](https://dados.tce.rs.gov.br/dataset/contratos-consolidado-2026)
- Municípios, malha e população (Censo 2022): [IBGE](https://servicodados.ibge.gov.br/api/docs/)

**Contexto e objetivo da base:** todo órgão fiscalizado pelo TCE-RS (prefeituras, câmaras, Estado, autarquias e consórcios)
é obrigado a registrar no LicitaCon cada processo de compra (licitação, dispensa ou inexigibilidade) e os contratos que
resultam dele. A base existe para dar **transparência** e permitir o **controle externo** das compras públicas. Os dados são
autodeclarados e não foram auditados.
""")
with c2, st.container(border=True):
    st.markdown(f"""
**População de interesse:** todos os processos de contratação com ano de licitação **2025 ou 2026** registrados até o
download: N = **{fmt_num(N, 0)}**.

**Unidade amostral:** a **licitação** (órgão + número + ano + modalidade). Contratos, aditivos e licitantes foram agregados
por licitação.

**Por que esta base:** é grande (centenas de milhares de registros), vem de uma fonte oficial e tem variáveis
**qualitativas** (modalidade, objeto, se gerou contrato) e **quantitativas** (nº de licitantes, desconto, valores, prazos).
Isso permite investigar parâmetros de **proporção** e de **média** com perguntas relevantes para o controle das compras
públicas.
""")
with st.container(border=True):
    st.markdown("**Como a população foi montada**")
    st.graphviz_chart(f"""
digraph {{
  rankdir=LR; bgcolor="transparent"; nodesep=0.3; ranksep=1.1;
  node [shape=box style="rounded,filled" fontname="Segoe UI" fontsize=13 margin="0.15,0.08"
  color="#c3c2b7" fillcolor="#ffffff" fontcolor="#0b0b0b"]; edge [color="#898781" arrowsize=0.6];
  lic [label="licitacao.csv\\n{fmt_num(N, 0)} licitações"];
  lt  [label="licitante.csv\\n{fmt_num(meta['n_registros_licitantes'], 0)} participações"];
  con [label="contrato.csv\\n{fmt_num(meta['n_registros_contratos'], 0)} contratos"];
  alt [label="alteracao.csv\\n{fmt_num(meta['n_registros_alteracoes'], 0)} aditivos"];
  ibge [label="IBGE\\n497 municípios + Censo 2022"];
  pop [label="População\\n1 linha por licitação · {pop.shape[1]} colunas" fillcolor="#cde2fb" color="#2a78d6"];
  amo [label="AAS sem reposição\\nn = {fmt_num(len(amo), 0)}" fillcolor="#fde3d7" color="#eb6834"];
  lic -> pop; lt -> pop [label=" nº licitantes" fontsize=11 fontcolor="#52514e"];
  con -> pop [label=" contrato, valor, vigência" fontsize=11 fontcolor="#52514e"]; alt -> con;
  ibge -> pop [label=" município" fontsize=11 fontcolor="#52514e"]; pop -> amo;
}}""", width="stretch")

st.markdown("#### Variáveis selecionadas")
variaveis = pd.DataFrame([
    ("Modalidade", "Qualitativa nominal", "licitação", "P1", "Dispensa (PRD, PDE), Inexigibilidade (PRI), Pregão (PCE, PCP), Concorrência (CCE, CCP), Outras. Grupos conferidos pela fundamentação legal (arts. 28, 74 e 75 da Lei 14.133)."),
    ("Tipo de objeto", "Qualitativa nominal", "licitação", "", "Compras, Outros serviços, Compras e serviços, Obras e serviços de engenharia, Outros (locação, saúde, informática, alienação, concessão)."),
    ("Tipo de órgão", "Qualitativa nominal", "licitação", "", "Prefeitura, Câmara de Vereadores ou Outros, pelo prefixo do nome do órgão."),
    ("Natureza do procedimento", "Qualitativa nominal", "licitação", "", "Normal, Registro de preços ou Outros."),
    ("Mesorregião / município", "Qualitativa nominal", "licitação + IBGE", "", "Para prefeituras e câmaras: município pelo nome do órgão (100% casados com o IBGE) e sua mesorregião."),
    ("Ano da licitação", "Qualitativa ordinal", "licitação", "", "2025 ou 2026 (2026 parcial)."),
    ("Permite consórcio", "Qualitativa binária", "licitação", "", "Se o edital admite empresas consorciadas."),
    ("Gerou contrato registrado", "Qualitativa binária", "contratos", "P2", "Se há ao menos um contrato com a chave da licitação."),
    ("Contrato com aditivo", "Qualitativa binária", "contratos", "", "Se algum contrato da licitação tem alteração registrada (só entre as que têm contrato)."),
    ("Valor de referência (R$)", "Quantitativa contínua", "licitação", "", "Homologado quando > 0, senão estimado. Valores > R$ 20 bi ou com estimado × homologado divergindo > 100× foram anulados como erro de cadastro."),
    ("Nº de licitantes", "Quantitativa discreta", "licitantes", "M1", "Licitantes distintos em pregão e concorrência."),
    ("Desconto homologado (%)", "Quantitativa contínua", "licitação", "M2", "1 − homologado ÷ estimado, em pregão e concorrência com os dois valores (homologado ≤ 2× estimado)."),
    ("Dias até a homologação", "Quantitativa discreta", "licitação", "", "Homologação − abertura, em pregão e concorrência (0 a 730 dias)."),
    ("Nº de contratos", "Quantitativa discreta", "contratos", "", "Contratos registrados por licitação (0 se nenhum)."),
    ("Valor contratado (R$)", "Quantitativa contínua", "contratos", "", "Soma do valor dos contratos da licitação."),
    ("Prazo de vigência (dias)", "Quantitativa contínua", "contratos", "", "Mediana do prazo dos contratos da licitação (1 a 3.650 dias)."),
], columns=["Variável", "Tipo", "Origem", "Hipótese", "Descrição"])
with st.container(border=True):
    st.table(variaveis.set_index("Variável"))
c1, c2 = st.columns([1, 1.3], gap="medium")
with c2, st.container(border=True):
    cols = {**QUALI, **QUANTI}
    preench = pd.Series({nome: pop[c].notna().mean() for c, nome in cols.items()}).sort_values(ascending=False)
    fig = g.ranking(preench, "% das licitações com a variável definida", fmt=".0%")
    fig.update_xaxes(tickformat=".0%", range=[0, 1.18])
    g.mostrar(fig, "preench", 400, "Cobertura de cada variável na população")
    leitura("Variáveis de **domínio** (licitantes, desconto, prazo) só existem em parte das licitações, por definição. "
            "Por isso as hipóteses de média trabalham com um n efetivo menor.")
with c1, st.container(border=True):
    st.markdown("**Tipos de variável**")
    tipos = variaveis["Tipo"].str.split().str[0].value_counts()
    st.markdown(f"- **{tipos.get('Qualitativa', 0)} qualitativas** (nominais, ordinal e binárias): frequências, proporções, "
                "testes de proporção e qui-quadrado.\n"
                f"- **{tipos.get('Quantitativa', 0)} quantitativas** (discretas e contínuas): média, mediana, desvio-padrão, "
                "quartis, assimetria, testes t e KS.\n"
                "- Valores em R$ são **log-normais**, por isso aparecem em escala log nos gráficos.")

secao("02", "Dimensionamento e seleção da amostra",
      "Tamanho de amostra para estimar uma proporção em população finita e sorteio por AAS sem reposição.")
c1, c2 = st.columns([1.1, 1], gap="large")
with c1, st.container(border=True):
    st.markdown("Mesma fórmula da [calculadora USP/Bauru](https://estatistica.bauru.usp.br/calculoamostral/ta_proporcao.php) "
                "para proporção com população finita:")
    st.latex(r"n = \frac{N \, z^2 \, p(1-p)}{E^2 (N-1) + z^2 \, p(1-p)}")
    st.latex(rf"n = \frac{{{N}\cdot{dim['z']:.3f}^2\cdot{ctx['p_plan']:.2f}\cdot{1 - ctx['p_plan']:.2f}}}"
             rf"{{{ctx['margem']:.3f}^2\cdot{N - 1} + {dim['z']:.3f}^2\cdot{ctx['p_plan']:.2f}\cdot{1 - ctx['p_plan']:.2f}}}"
             rf" = {dim['n_exato']:.2f}".replace(".", "{,}"))
    st.latex(rf"\Rightarrow n = \lceil {dim['n_exato']:.2f} \rceil = {dim['n']}".replace(".", "{,}"))
    st.markdown(f"""
| Parâmetro | Valor | Justificativa |
|---|---|---|
| N | {fmt_num(N, 0)} | Tamanho da população |
| Confiança | {fmt_pct(ctx['conf_dim'], 0)} (z = {fmt_num(dim['z'], 3)}) | Padrão em estudos descritivos; mesmo nível dos ICs do Painel 3 |
| Margem de erro (E) | {fmt_pct(ctx['margem'], 1)} | Mais estreita que os 5% usuais porque as hipóteses de média usam só o **domínio** de pregões e concorrências (~22% da população). Com E = 5% (n = 384) esse domínio teria só ~80 unidades |
| Proporção (p) | {fmt_num(ctx['p_plan'], 2)} | Variância máxima (cenário conservador); as proporções testadas (P1, P2) estão perto de 50% |

**Resultado:** n₀ = {fmt_num(dim['n0'], 1)} (população infinita) → **n = {fmt_num(dim['n'], 0)} licitações**
({fmt_pct(dim['fracao'], 2)} da população). Com uma fração tão pequena, a correção para população finita quase não muda nada.
""")
with c2:
    with st.container(border=True):
        g.mostrar(g.tamanho_vs_margem(N, ctx["conf_dim"], ctx["p_plan"], ctx["margem"], tamanho_amostra), "n_margem", 300,
                  "Quanto a amostra cresce ao apertar a margem de erro")
        leitura(f"n cresce com 1/E²: reduzir a margem de 5% para {fmt_pct(ctx['margem'], 0)} multiplica o n por cerca de "
                f"{fmt_num((0.05 / ctx['margem']) ** 2, 1)}. Ainda assim é menos de 1% da população, um custo pequeno para "
                "ter centenas de unidades nos domínios das médias.")
    with st.container(border=True):
        st.markdown("**Procedimento da AAS (sem reposição)**")
        st.markdown(f"""
1. A população é ordenada pela chave da licitação (ordem fixa e reprodutível).
2. Um gerador pseudoaleatório (`numpy.random.default_rng`) com semente **{ctx['semente']}** sorteia **n posições distintas**
   entre 0 e N−1. Cada licitação tem a mesma probabilidade de entrar, **n/N = {fmt_pct(len(amo) / N, 3)}**, e todo
   subconjunto de tamanho n é igualmente provável.
3. As linhas sorteadas formam a amostra (`data/amostra.parquet`).
""")
        st.code(f"rng = np.random.default_rng({ctx['semente']})\nidx = rng.choice({N}, size={len(amo)}, replace=False)\n"
                "amostra = populacao.iloc[np.sort(idx)]", language="python")

with st.container(border=True):
    st.markdown("**Os sorteados se espalham por toda a população** (posição de cada licitação sorteada na lista ordenada)")
    fig = go.Figure(go.Histogram(x=amo["ID"], xbins=dict(start=0, end=N, size=N / 50),
                                 marker=dict(color=g.COR_AMO, line=dict(color="#fcfcfb", width=1)),
                                 hovertemplate="posições %{x}<br>%{y} sorteadas<extra></extra>"))
    esp = len(amo) / 50
    fig.add_hline(y=esp, line=dict(color=g.TINTA_2, width=1.5))
    fig.add_annotation(x=N, y=esp, text=f"esperado por faixa ≈ {fmt_num(esp, 0)}", showarrow=False, xanchor="right",
                       yanchor="bottom", font=dict(color=g.TINTA_2, size=11), bgcolor="rgba(252,252,251,0.9)")
    fig.update_xaxes(title="posição na população ordenada (ID)", tickformat=",.0f", showgrid=False)
    fig.update_yaxes(title="sorteadas por faixa")
    g.mostrar(fig, "unif", 230)
    leitura("Com probabilidade igual para todos, as sorteadas se distribuem de forma uniforme ao longo da lista, sem buracos nem "
            "aglomerações além da variação aleatória. A aderência variável a variável está no Painel 2.")

with st.expander("Prévia e download da amostra"):
    st.dataframe(amo.head(50), hide_index=True, width="stretch")
    st.download_button("Baixar a amostra (CSV)", amo.to_csv(index=False).encode("utf-8-sig"), "amostra_licitacoes.csv",
                       "text/csv", icon=":material/download:")
if ctx["personalizar"]:
    st.info("Você está vendo uma amostra personalizada (barra lateral). Desligue a opção para voltar à amostra oficial.")
