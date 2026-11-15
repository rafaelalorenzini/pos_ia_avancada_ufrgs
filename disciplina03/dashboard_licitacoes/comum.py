"""Dados, formatação e estado compartilhados pelas páginas do dashboard."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from scipy import stats

from estatistica import sortear_aas, tamanho_amostra

DATA = Path(__file__).parent / "data"

# ----------------------------------------------------------------------------- variáveis
QUALI = {
    "MODALIDADE_GRUPO": "Modalidade",
    "OBJETO": "Tipo de objeto",
    "TIPO_ORGAO": "Tipo de órgão",
    "NATUREZA": "Natureza do procedimento",
    "MESORREGIAO": "Mesorregião (órgãos municipais)",
    "ANO": "Ano da licitação",
    "PERMITE_CONSORCIO": "Permite consórcio",
    "TEM_CONTRATO": "Gerou contrato registrado",
    "TEM_ADITIVO": "Contrato com aditivo (entre as que têm contrato)",
}
QUANTI = {
    "VL_REF": "Valor de referência (R$)",
    "N_LICITANTES": "Nº de licitantes (pregão e concorrência)",
    "DESCONTO_PCT": "Desconto homologado (%)",
    "DIAS_ATE_HOMOLOGACAO": "Dias da abertura à homologação",
    "N_CONTRATOS": "Nº de contratos por licitação",
    "VL_CONTRATADO": "Valor contratado (R$)",
    "PRAZO_VIGENCIA_DIAS": "Prazo de vigência do contrato (dias)",
}
ORDEM = {
    "MODALIDADE_GRUPO": ["Dispensa", "Inexigibilidade", "Pregão", "Concorrência", "Outras"],
    "OBJETO": ["Compras", "Outros serviços", "Compras e serviços", "Obras e serv. de engenharia", "Outros"],
    "TIPO_ORGAO": ["Prefeitura", "Câmara de Vereadores", "Outros (Estado, autarquias, consórcios…)"],
    "NATUREZA": ["Normal", "Registro de preços", "Outros"],
}
ROTULO_BOOL = {True: "Sim", False: "Não"}


# ----------------------------------------------------------------------------- dados
@st.cache_resource(show_spinner="Carregando a população…")
def carregar():
    """População, amostra oficial, municípios e metadados (somente leitura: não modificar)."""
    if not (DATA / "populacao.parquet").exists():
        st.error("Rode antes `uv run python preparar_dados.py` para montar a população e a amostra.")
        st.stop()
    pop = pd.read_parquet(DATA / "populacao.parquet")
    amo = pd.read_parquet(DATA / "amostra.parquet")
    mun = pd.read_parquet(DATA / "municipios.parquet")
    meta = json.loads((DATA / "metadados.json").read_text(encoding="utf-8"))
    geo = orientar_horario(json.loads((DATA / "ibge" / "malha_rs.geojson").read_text(encoding="utf-8")))
    return pop, amo, mun, meta, geo


def _area(anel) -> float:
    xy = np.asarray(anel)
    return 0.5 * float(np.sum(xy[:-1, 0] * xy[1:, 1] - xy[1:, 0] * xy[:-1, 1]))


def orientar_horario(geo: dict) -> dict:
    """A malha do IBGE segue a RFC 7946 (anel externo anti-horário); o Plotly (d3-geo) espera horário.

    Sem inverter, cada município vira o "resto do mundo" e o mapa aparece como um retângulo cheio.
    """
    for f in geo["features"]:
        geom = f["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        for poly in polys:
            for i, anel in enumerate(poly):
                externo = i == 0
                if (_area(anel) > 0) == externo:   # externo anti-horário ou buraco horário → inverte
                    poly[i] = anel[::-1]
    return geo


@st.cache_resource(show_spinner="Sorteando a amostra…")
def amostra_personalizada(n: int, semente: int) -> pd.DataFrame:
    pop = carregar()[0]
    return sortear_aas(pop, n, semente)


def montar_contexto(personalizar: bool, conf_dim: float, margem: float, p_plan: float, semente: int) -> dict:
    pop, amo_oficial, mun, meta, geo = carregar()
    dim = tamanho_amostra(len(pop), conf_dim, margem, p_plan)
    amostra = amostra_personalizada(dim["n"], int(semente)) if personalizar else amo_oficial
    return dict(pop=pop, amostra=amostra, mun=mun, meta=meta, geo=geo, dim=dim, personalizar=personalizar,
                conf_dim=conf_dim, margem=margem, p_plan=p_plan, semente=int(semente))


def contexto() -> dict:
    return st.session_state["ctx"]


# ----------------------------------------------------------------------------- formatação pt-BR
def fmt_num(v, casas=2):
    if v is None or pd.isna(v):
        return "—"
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(v, casas=1):
    return "—" if v is None or pd.isna(v) else fmt_num(v * 100, casas) + "%"


def fmt_rs(v):
    if v is None or pd.isna(v):
        return "—"
    for lim, suf in [(1e9, " bi"), (1e6, " mi"), (1e3, " mil")]:
        if abs(v) >= lim:
            return "R$ " + fmt_num(v / lim, 1) + suf
    return "R$ " + fmt_num(v, 2)


def fmt_p(p):
    return f"{p:.4f}".replace(".", ",") if p >= 1e-4 else f"{p:.1e}".replace(".", ",")


# ----------------------------------------------------------------------------- estatística descritiva
def serie_quali(df: pd.DataFrame, col: str) -> pd.Series:
    s = df[col].dropna()
    if s.dtype == bool or str(s.dtype) == "boolean":
        s = s.astype(bool).map(ROTULO_BOOL)
    return s.astype(str)


def frequencias(df: pd.DataFrame, col: str) -> pd.DataFrame:
    s = serie_quali(df, col)
    f = s.value_counts().rename("Frequência").to_frame()
    f["Proporção"] = f["Frequência"] / f["Frequência"].sum()
    if col in ORDEM:
        f = f.reindex([c for c in ORDEM[col] if c in f.index])
    elif col == "ANO":
        f = f.sort_index()
    f.index.name = col
    return f


def medidas(x: pd.Series) -> pd.Series:
    x = x.dropna().astype(float)
    return pd.Series({
        "n": len(x), "Média": x.mean(), "Mediana": x.median(), "Desvio-padrão": x.std(ddof=1),
        "Coef. de variação": x.std(ddof=1) / x.mean() if x.mean() else np.nan,
        "Mínimo": x.min(), "Q1": x.quantile(.25), "Q3": x.quantile(.75), "Máximo": x.max(),
        "Assimetria": stats.skew(x) if len(x) > 2 else np.nan,
    })


def fmt_medidas(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().astype(object)
    for i in out.index:
        for c in out.columns:
            v = df.loc[i, c]
            out.loc[i, c] = fmt_num(v, 0) if i == "n" else fmt_num(v, 3 if i in ("Coef. de variação", "Assimetria") else 2)
    return out


def ultimo_mes_completo(meta: dict) -> pd.Timestamp:
    """Último mês inteiro antes do download (o mês do download está incompleto)."""
    d = pd.to_datetime(meta["data_download"], dayfirst=True)
    return (d.to_period("M") - 1).to_timestamp()


# ----------------------------------------------------------------------------- componentes visuais
CSS = """
<style>
  .block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1400px;}
  h1 {font-weight: 700; letter-spacing: -0.02em;}
  h2, h3 {letter-spacing: -0.01em;}
  .hero {border-left: 4px solid var(--hero-cor, #2a78d6); padding: 0.2rem 0 0.2rem 1rem; margin-bottom: 1.2rem;}
  .hero .kicker {text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.08em; color: #52514e; font-weight: 600;}
  .hero h1 {margin: 0.15rem 0 0.3rem 0; padding: 0; font-size: 2.1rem; line-height: 1.15;}
  .hero p {color: #52514e; margin: 0; font-size: 1.02rem; max-width: 70rem;}
  .secao {margin: 2.2rem 0 0.4rem 0; padding-bottom: 0.35rem; border-bottom: 1px solid #e1e0d9;}
  .secao .num {color: #898781; font-weight: 600; margin-right: 0.5rem;}
  .secao h2 {display: inline; font-size: 1.35rem; margin: 0; padding: 0;}
  .secao p {color: #52514e; margin: 0.25rem 0 0 0; font-size: 0.95rem;}
  .titulo-grafico {font-weight: 600; font-size: 0.98rem; color: #0b0b0b; margin: 0.1rem 0 -0.2rem 0;}
  .leitura {background: #f3f2ee; border-radius: 8px; padding: 0.7rem 0.9rem; color: #2b2b29; font-size: 0.93rem;
            margin: 0.2rem 0 0.6rem 0;}
  .leitura b {color: #0b0b0b;}
  .chip {display: inline-block; padding: 0.1rem 0.55rem; border-radius: 999px; font-size: 0.78rem; font-weight: 600;
         margin-right: 0.3rem; border: 1px solid #e1e0d9; color: #52514e; background: #fcfcfb;}
  .chip.ok {color: #006300; border-color: #b9dcb9; background: #f1f8f1;}
  .chip.alerta {color: #8a4b00; border-color: #f0d29a; background: #fff8ea;}
  div[data-testid="stMetric"] {background: #ffffff;}
  div[data-testid="stMetricLabel"] p {font-size: 0.8rem; color: #52514e;}
  div[data-testid="stMetricValue"] {font-size: 1.4rem; font-weight: 600;}
  div[data-testid="stMetricDelta"] {font-size: 0.78rem;}
  [data-testid="stSidebar"] .sidebar-titulo {font-weight: 700; font-size: 1.05rem; margin-bottom: -0.5rem;}
</style>
"""


def aplicar_css():
    st.markdown(CSS, unsafe_allow_html=True)


def hero(kicker: str, titulo: str, texto: str, cor: str = "#2a78d6"):
    st.markdown(f'<div class="hero" style="--hero-cor:{cor}"><div class="kicker">{kicker}</div>'
                f'<h1>{titulo}</h1><p>{texto}</p></div>', unsafe_allow_html=True)


def secao(num: str, titulo: str, texto: str = ""):
    st.markdown(f'<div class="secao"><span class="num">{num}</span><h2>{titulo}</h2>'
                + (f"<p>{texto}</p>" if texto else "") + "</div>", unsafe_allow_html=True)


def leitura(texto: str):
    """Caixa 'como ler / o que se conclui' abaixo de um gráfico (aceita **negrito** em markdown simples)."""
    import re
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", texto)
    st.markdown(f'<div class="leitura">{html}</div>', unsafe_allow_html=True)


def chip(texto: str, tipo: str = "") -> str:
    return f'<span class="chip {tipo}">{texto}</span>'
