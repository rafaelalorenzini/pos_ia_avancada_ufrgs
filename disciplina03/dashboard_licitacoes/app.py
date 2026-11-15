"""Dashboard da prova final: licitações e contratos do TCE-RS (2025-2026).

Uso:  uv run streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Licitações RS · Amostragem e inferência", page_icon=":material/query_stats:",
                   layout="wide", initial_sidebar_state="expanded")

from comum import aplicar_css, carregar, fmt_num, montar_contexto  # noqa: E402

aplicar_css()
pop, amo_oficial, mun, meta, geo = carregar()

# ----------------------------------------------------------------------------- navegação
paginas = [
    st.Page("paginas/base.py", title="Base e amostragem", icon=":material/database:", default=True),
    st.Page("paginas/populacao.py", title="Painel 1 · População", icon=":material/groups:"),
    st.Page("paginas/amostra.py", title="Painel 2 · Amostra", icon=":material/filter_alt:"),
    st.Page("paginas/inferencia.py", title="Painel 3 · Inferência", icon=":material/functions:"),
]
nav = st.navigation(paginas)

# ----------------------------------------------------------------------------- amostra (barra lateral)
with st.sidebar:
    st.markdown('<div class="sidebar-titulo">Licitações RS</div>', unsafe_allow_html=True)
    st.caption("LicitaCon · TCE-RS · 2025–2026")
    st.divider()
    personalizar = st.toggle("Sortear outra amostra", value=False,
                             help="Desligado = amostra oficial do trabalho. Ligado = refaz o dimensionamento e o sorteio.")
    if personalizar:
        conf_dim = st.select_slider("Confiança do dimensionamento", [0.90, 0.95, 0.99], value=meta["confianca"],
                                    format_func=lambda v: f"{v:.0%}")
        margem = st.select_slider("Margem de erro", [0.01, 0.015, 0.02, 0.03, 0.04, 0.05], value=meta["margem"],
                                  format_func=lambda v: f"{v:.1%}".replace(".", ","))
        p_plan = st.slider("Proporção de planejamento", 0.05, 0.95, meta["p_planejamento"], 0.05)
        semente = st.number_input("Semente", value=meta["semente"], step=1)
    else:
        conf_dim, margem, p_plan, semente = meta["confianca"], meta["margem"], meta["p_planejamento"], meta["semente"]
    ctx = montar_contexto(personalizar, conf_dim, margem, p_plan, semente)
    st.session_state["ctx"] = ctx
    rot = "Amostra personalizada" if personalizar else "Amostra oficial"
    st.caption(f"{rot}: n = **{fmt_num(len(ctx['amostra']), 0)}** · semente {ctx['semente']}")
    st.divider()
    st.caption(f"Dados baixados em {meta['data_download']}. Os conjuntos de 2025 e 2026 são atualizados diariamente "
               "pelo TCE-RS; municípios e população: IBGE (Censo 2022).")

nav.run()
