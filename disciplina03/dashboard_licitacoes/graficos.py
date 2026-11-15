"""Template Plotly único e funções de gráfico reutilizadas pelos painéis.

Paleta (validada com o validador da skill dataviz, modo claro, superfície #fcfcfb):
  categórica em ordem fixa  #2a78d6 #eb6834 #1baf7a #eda100 #e87ba4  (5 slots, todos os checks passam)
  população = slot 1 (azul), amostra = slot 2 (laranja)
  sequencial = rampa azul de um só tom, claro → escuro
  divergente = azul ↔ vermelho com meio cinza
Os slots 3–5 ficam abaixo de 3:1 de contraste, então todo gráfico com eles leva rótulo ou legenda visível.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

COR_POP, COR_AMO = "#2a78d6", "#eb6834"
CATEGORICAS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
SEQ_AZUL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGENTE = [[0, "#d03b3b"], [0.5, "#f0efec"], [1, "#2a78d6"]]
TINTA, TINTA_2, MUDO = "#0b0b0b", "#52514e", "#898781"
GRADE, EIXO, NEUTRA = "#e1e0d9", "#c3c2b7", "#8a8984"
FONTE = 'Inter, "Segoe UI", system-ui, -apple-system, sans-serif'

pio.templates["licitacoes"] = go.layout.Template(layout=dict(
    font=dict(family=FONTE, size=13, color=TINTA_2),
    title=dict(font=dict(size=15, color=TINTA), x=0, xanchor="left", y=0.98, yanchor="top"),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    colorway=CATEGORICAS, separators=",.",
    xaxis=dict(gridcolor=GRADE, linecolor=EIXO, zerolinecolor=EIXO, ticks="", title=dict(font=dict(size=12, color=MUDO)),
               tickfont=dict(color=MUDO), automargin=True),
    yaxis=dict(gridcolor=GRADE, linecolor=EIXO, zerolinecolor=EIXO, ticks="", title=dict(font=dict(size=12, color=MUDO)),
               tickfont=dict(color=MUDO), automargin=True),
    legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, xanchor="left", title_text="",
                font=dict(color=TINTA_2), bgcolor="rgba(0,0,0,0)"),
    hoverlabel=dict(bgcolor="#ffffff", bordercolor=GRADE, font=dict(family=FONTE, color=TINTA, size=12)),
    bargap=0.25, bargroupgap=0.08,
    margin=dict(l=8, r=12, t=56, b=8),
))
pio.templates.default = "licitacoes"

CONFIG = {"displayModeBar": False}
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def eixo_meses(fig, inicio, fim, passo=2):
    """Rótulos de mês em português (o Plotly do Streamlit não carrega o locale pt-BR)."""
    meses = pd.date_range(inicio, fim, freq="MS")[::passo]
    fig.update_xaxes(tickvals=meses, ticktext=[f"{MESES[m.month - 1]}/{m.strftime('%y')}" for m in meses])


def eixo_log(fig, eixo: str, vmin: float, vmax: float):
    pots = [10 ** k for k in range(int(np.floor(np.log10(vmin))), int(np.ceil(np.log10(vmax))) + 1)]
    rot = [_rotulo_pot(int(np.log10(p))) for p in pots]
    (fig.update_xaxes if eixo == "x" else fig.update_yaxes)(tickvals=pots, ticktext=rot, minor=dict(showgrid=False))


def mostrar(fig: go.Figure, key: str, altura: int = 360, titulo: str | None = None):
    """Título como cabeçalho do card (fora do Plotly), para a legenda nunca colidir com ele em cards estreitos."""
    if titulo:
        st.markdown(f'<div class="titulo-grafico">{titulo}</div>', unsafe_allow_html=True)
    tem_legenda = fig.layout.showlegend is not False and len(fig.data) > 1
    topo = fig.layout.margin.t if fig.layout.margin.t not in (None, 56) else (34 if tem_legenda else 8)
    fig.update_layout(height=altura - (24 if titulo else 0), title=None, margin=dict(t=topo))
    st.plotly_chart(fig, key=key, config=CONFIG, theme=None, width="stretch")


def cores_categorias(categorias) -> dict:
    """Cor segue a categoria (ordem fixa), nunca a posição no ranking."""
    return {c: CATEGORICAS[i % len(CATEGORICAS)] for i, c in enumerate(categorias)}


# ----------------------------------------------------------------------------- barras
def barras_freq(f: pd.DataFrame, fr: pd.DataFrame | None, rotulo: str, cor: str = COR_POP) -> go.Figure:
    """Barras horizontais de proporção; com `fr` (população) vira comparação agrupada população × amostra."""
    fig = go.Figure()
    cats = list(f.index) if fr is None else list(dict.fromkeys(list(fr.index) + list(f.index)))
    if fr is not None:
        fig.add_bar(y=cats, x=fr["Proporção"].reindex(cats).fillna(0), name="População", orientation="h",
                    marker=dict(color=COR_POP, cornerradius=4), text=fr["Proporção"].reindex(cats).fillna(0),
                    texttemplate="%{text:.1%}", textposition="outside", cliponaxis=False,
                    hovertemplate="%{y}<br>População: %{x:.2%}<extra></extra>")
    fig.add_bar(y=cats, x=f["Proporção"].reindex(cats).fillna(0), name="Amostra" if fr is not None else rotulo,
                orientation="h", marker=dict(color=COR_AMO if fr is not None else cor, cornerradius=4),
                text=f["Proporção"].reindex(cats).fillna(0), texttemplate="%{text:.1%}", textposition="outside",
                cliponaxis=False, customdata=f["Frequência"].reindex(cats).fillna(0),
                hovertemplate="%{y}<br>%{x:.2%} (%{customdata:,.0f} licitações)<extra></extra>")
    xmax = max(f["Proporção"].max(), fr["Proporção"].max() if fr is not None else 0)
    fig.update_xaxes(tickformat=".0%", range=[0, xmax * 1.22], showgrid=True, title=None)
    fig.update_yaxes(autorange="reversed", title=None, showgrid=False)
    fig.update_layout(barmode="group", showlegend=fr is not None, bargap=0.3 if fr is not None else 0.35)
    return fig


def barras_taxa_por_grupo(df: pd.DataFrame, ref: pd.DataFrame | None, grupo: str, col: str, ordem: list[str]) -> go.Figure:
    """% de um evento (coluna booleana) por categoria, em barras horizontais; população × amostra quando há `ref`."""
    def taxa(d):
        return d.groupby(grupo)[col].apply(lambda s: s.dropna().astype(bool).mean()).reindex(ordem)
    fig = go.Figure()
    if ref is not None:
        t = taxa(ref)
        fig.add_bar(y=t.index, x=t.values, name="População", orientation="h", marker=dict(color=COR_POP, cornerradius=4),
                    text=t.values, texttemplate="%{text:.0%}", textposition="outside", cliponaxis=False,
                    hovertemplate="%{y}<br>População: %{x:.1%}<extra></extra>")
    t = taxa(df)
    fig.add_bar(y=t.index, x=t.values, name="Amostra" if ref is not None else "", orientation="h", text=t.values,
                texttemplate="%{text:.0%}", textposition="outside", cliponaxis=False,
                marker=dict(color=COR_AMO if ref is not None else COR_POP, cornerradius=4),
                hovertemplate="%{y}<br>%{x:.1%}<extra></extra>")
    fig.update_xaxes(tickformat=".0%", range=[0, 1.15], title=None)
    fig.update_yaxes(title=None, showgrid=False, autorange="reversed")
    fig.update_layout(barmode="group", showlegend=ref is not None)
    return fig


def ranking(serie: pd.Series, rotulo_x: str, cor: str = COR_POP, fmt: str = ",.0f") -> go.Figure:
    fig = go.Figure(go.Bar(y=serie.index, x=serie.values, orientation="h", marker=dict(color=cor, cornerradius=4),
                           text=serie.values, texttemplate=f"%{{text:{fmt}}}", textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}<br>%{x:" + fmt + "}<extra></extra>"))
    fig.update_yaxes(autorange="reversed", title=None, showgrid=False, tickfont=dict(size=11))
    fig.update_xaxes(title=rotulo_x, range=[0, serie.max() * 1.18])
    return fig


# ----------------------------------------------------------------------------- composição
def treemap(df: pd.DataFrame, nivel1: str, nivel2: str, ordem1: list[str]) -> go.Figure:
    g = df.groupby([nivel1, nivel2]).size().rename("n").reset_index()
    tot = g.groupby(nivel1)["n"].sum()
    cores = cores_categorias(ordem1)
    ids, labels, parents, values, colors = [], [], [], [], []
    for a in [c for c in ordem1 if c in tot.index]:
        ids.append(a); labels.append(a); parents.append(""); values.append(int(tot[a])); colors.append(cores[a])
        for _, r in g[g[nivel1] == a].sort_values("n", ascending=False).iterrows():
            ids.append(f"{a}/{r[nivel2]}"); labels.append(r[nivel2]); parents.append(a); values.append(int(r["n"]))
            colors.append(cores[a])
    fig = go.Figure(go.Treemap(
        ids=ids, labels=labels, parents=parents, values=values, branchvalues="total",
        marker=dict(colors=colors, line=dict(color="#fcfcfb", width=2)),
        texttemplate="<b>%{label}</b><br>%{percentRoot:.1%}", textfont=dict(color="#ffffff", family=FONTE),
        hovertemplate="%{id}<br>%{value:,.0f} licitações<br>%{percentRoot:.1%} do total · %{percentParent:.1%} do grupo<extra></extra>",
        tiling=dict(pad=2), pathbar=dict(visible=False), root=dict(color="#fcfcfb"),
    ))
    fig.update_layout(margin=dict(l=0, r=0, t=8, b=0))
    return fig


def heatmap_cruzado(df: pd.DataFrame, linhas: str, colunas: str, ordem_l: list[str], ordem_c: list[str],
                    ref: pd.DataFrame | None = None) -> go.Figure:
    """% na linha (cada linha soma 100%). Com `ref`, o hover mostra também o valor da população."""
    def tab(d):
        t = pd.crosstab(d[linhas], d[colunas], normalize="index")
        return t.reindex(index=[x for x in ordem_l if x in t.index], columns=[x for x in ordem_c if x in t.columns]).fillna(0)
    t = tab(df)
    custom = None
    hover = "%{y} → %{x}<br>%{z:.1%} da linha<extra></extra>"
    if ref is not None:
        tr = tab(ref).reindex(index=t.index, columns=t.columns).fillna(0)
        custom = tr.values
        hover = "%{y} → %{x}<br>Amostra: %{z:.1%}<br>População: %{customdata:.1%}<extra></extra>"
    rotulos = [[c.replace(" (Estado, autarquias, consórcios…)", "") for c in t.columns]][0]
    fig = go.Figure(go.Heatmap(
        z=t.values, x=rotulos, y=list(t.index), customdata=custom, colorscale=[[i / 6, c] for i, c in enumerate(SEQ_AZUL)],
        zmin=0, zmax=1, xgap=2, ygap=2, text=t.values, texttemplate="%{text:.0%}",
        hovertemplate=hover, colorbar=dict(tickformat=".0%", thickness=10, outlinewidth=0, len=0.9),
    ))
    fig.update_yaxes(autorange="reversed", showgrid=False, title=None)
    fig.update_xaxes(showgrid=False, title=None, tickangle=0)
    return fig


# ----------------------------------------------------------------------------- tempo
def serie_mensal(df: pd.DataFrame, grupo: str, ordem: list[str], ate: pd.Timestamp, desde="2025-01-01") -> go.Figure:
    d = df[(df["MES_ABERTURA"] >= desde) & (df["MES_ABERTURA"] <= ate)]
    t = d.groupby(["MES_ABERTURA", grupo]).size().unstack(fill_value=0).reindex(columns=ordem, fill_value=0)
    cores = cores_categorias(ordem)
    fig = go.Figure()
    for c in ordem:
        fig.add_scatter(x=t.index, y=t[c], name=c, mode="lines", stackgroup="um", line=dict(width=0.8, color=cores[c]),
                        fillcolor=cores[c], hovertemplate=f"{c}: %{{y:,.0f}}<extra></extra>")
    fig.update_xaxes(showgrid=False, title=None)
    eixo_meses(fig, desde, ate)
    fig.update_yaxes(title="licitações abertas no mês", tickformat=",.0f")
    fig.update_layout(hovermode="x unified")
    return fig


def serie_mensal_comparada(df: pd.DataFrame, ref: pd.DataFrame, ate: pd.Timestamp, desde="2025-01-01") -> go.Figure:
    """Distribuição das licitações por mês (% do total) — população × amostra na mesma escala."""
    fig = go.Figure()
    for d, nome, cor in [(ref, "População", COR_POP), (df, "Amostra", COR_AMO)]:
        x = d[(d["MES_ABERTURA"] >= desde) & (d["MES_ABERTURA"] <= ate)]["MES_ABERTURA"].value_counts(normalize=True).sort_index()
        fig.add_scatter(x=x.index, y=x.values, name=nome, mode="lines+markers", line=dict(color=cor, width=2),
                        marker=dict(size=7, line=dict(color="#fcfcfb", width=2)),
                        hovertemplate=nome + ": %{y:.2%}<extra></extra>")
    fig.update_xaxes(showgrid=False, title=None)
    eixo_meses(fig, desde, ate)
    fig.update_yaxes(tickformat=".1%", title="% das licitações do período", rangemode="tozero")
    fig.update_layout(hovermode="x unified")
    return fig


# ----------------------------------------------------------------------------- território
def mapa(geo: dict, por_mun: pd.DataFrame, coluna: str, rotulo: str, fmt: str, log: bool = False) -> go.Figure:
    """Coroplético dos 497 municípios do RS (malha IBGE). `por_mun` tem COD_IBGE, MUNICIPIO e a métrica."""
    z = por_mun[coluna].astype(float)
    zc = np.log10(z.clip(lower=1)) if log else z
    ticks = None
    if log:
        lo, hi = int(np.floor(zc.min())), int(np.ceil(zc.max()))
        ticks = dict(tickvals=list(range(lo, hi + 1)),
                     ticktext=[f"{10 ** v:,.0f}".replace(",", ".") for v in range(lo, hi + 1)])
    else:
        zmax = float(np.nanquantile(z, 0.98))  # o top 2% satura a cor e não achata o resto do mapa
    fig = go.Figure(go.Choropleth(
        geojson=geo, featureidkey="properties.codarea", locations=por_mun["COD_IBGE"], z=zc,
        zmin=None if log else 0, zmax=None if log else zmax,
        colorscale=[[i / 6, c] for i, c in enumerate(SEQ_AZUL)], marker=dict(line=dict(color="#fcfcfb", width=0.4)),
        customdata=np.stack([por_mun["MUNICIPIO"], z], axis=1),
        hovertemplate="<b>%{customdata[0]}</b><br>" + rotulo + ": %{customdata[1]:" + fmt + "}<extra></extra>",
        colorbar=dict(title=dict(text=rotulo, side="right", font=dict(size=11, color=MUDO)), thickness=10,
                      outlinewidth=0, len=0.8, tickfont=dict(color=MUDO), **(ticks or {})),
    ))
    fig.update_geos(projection_type="mercator", lonaxis_range=[-57.8, -49.5], lataxis_range=[-33.9, -27.0],
                    visible=False, bgcolor="rgba(0,0,0,0)", domain=dict(x=[0, 0.9], y=[0, 1]))
    fig.update_layout(margin=dict(l=0, r=0, t=8, b=0), dragmode=False)
    return fig


def dispersao_municipios(por_mun: pd.DataFrame) -> go.Figure:
    """Licitações × habitantes (log-log), com a reta de tendência em escala log."""
    d = por_mun[(por_mun["POP_2022"] > 0) & (por_mun["LICITACOES"] > 0)]
    lx, ly = np.log10(d["POP_2022"]), np.log10(d["LICITACOES"])
    b, a = np.polyfit(lx, ly, 1)
    xs = np.linspace(lx.min(), lx.max(), 50)
    fig = go.Figure()
    fig.add_scatter(x=d["POP_2022"], y=d["LICITACOES"], mode="markers", name="Municípios",
                    marker=dict(size=8, color=COR_POP, opacity=0.65, line=dict(color="#fcfcfb", width=1)),
                    customdata=np.stack([d["MUNICIPIO"], d["POR_MIL_HAB"]], axis=1),
                    hovertemplate="<b>%{customdata[0]}</b><br>%{x:,.0f} habitantes<br>%{y:,.0f} licitações"
                                  "<br>%{customdata[1]:,.1f} por 1.000 hab.<extra></extra>")
    fig.add_scatter(x=10 ** xs, y=10 ** (a + b * xs), mode="lines", name=f"tendência (elasticidade {b:.2f})".replace(".", ","),
                    line=dict(color=TINTA_2, width=2), hoverinfo="skip")
    fig.update_xaxes(type="log", title="habitantes (Censo 2022, escala log)")
    fig.update_yaxes(type="log", title="licitações 2025–2026 (escala log)")
    eixo_log(fig, "x", d["POP_2022"].min(), d["POP_2022"].max())
    eixo_log(fig, "y", d["LICITACOES"].min(), d["LICITACOES"].max())
    return fig, b


# ----------------------------------------------------------------------------- distribuições
def histograma(x: pd.Series, ref: pd.Series | None, rotulo: str, log: bool = False, cor: str = COR_POP,
               nbins: int = 45, linha_media: bool = False, corte_sup: float | None = None,
               corte_inf: float | None = None) -> go.Figure:
    """Histograma pré-agregado (np.histogram), leve mesmo com 300 mil linhas.

    Sem `ref`: barras de contagem. Com `ref`: população em barras e amostra em linha-degrau, ambas em proporção.
    """
    def prep(s):
        s = s.dropna().astype(float)
        if corte_sup is not None:
            s = s.clip(upper=corte_sup)
        if corte_inf is not None:
            s = s.clip(lower=corte_inf)
        return np.log10(s[s >= 1]) if log else s   # em log, a exibição começa em 1 (centavos são erro de cadastro)
    px_, pr = prep(x), (prep(ref) if ref is not None else None)
    base = pd.concat([px_, pr]) if pr is not None else px_
    ini, fim = float(base.min()), float(base.max())
    discreto = not log and np.allclose(base, np.round(base)) and (fim - ini) <= 80
    bordas = np.arange(ini - 0.5, fim + 1.5, 1.0) if discreto else np.linspace(ini, fim, nbins + 1)
    centros, largura = (bordas[:-1] + bordas[1:]) / 2, np.diff(bordas)
    fig = go.Figure()
    rot_x = [_rotulo_pot_cont(c) for c in centros] if log else [fmt_br(c, 0 if discreto else 1) for c in centros]
    if pr is not None:
        hp = np.histogram(pr, bordas)[0] / len(pr)
        ha = np.histogram(px_, bordas)[0] / len(px_)
        fig.add_bar(x=centros, y=hp, width=largura, name="População", marker=dict(color=COR_POP, opacity=0.45,
                    line=dict(color="#fcfcfb", width=1)), customdata=rot_x,
                    hovertemplate="%{customdata}<br>População: %{y:.2%}<extra></extra>")
        fig.add_scatter(x=np.r_[bordas[0], np.repeat(bordas[1:-1], 2), bordas[-1]], y=np.repeat(ha, 2), mode="lines",
                        name="Amostra", line=dict(color=COR_AMO, width=2.5), hoverinfo="skip")
        fig.add_scatter(x=centros, y=ha, mode="markers", marker=dict(size=14, opacity=0), showlegend=False,
                        customdata=rot_x, hovertemplate="%{customdata}<br>Amostra: %{y:.2%}<extra></extra>")
        fig.update_yaxes(tickformat=".0%", title="proporção das licitações")
    else:
        h = np.histogram(px_, bordas)[0]
        fig.add_bar(x=centros, y=h, width=largura, name=rotulo, marker=dict(color=cor, line=dict(color="#fcfcfb", width=1)),
                    customdata=rot_x, hovertemplate="%{customdata}<br>%{y:,.0f} licitações<extra></extra>")
        fig.update_yaxes(tickformat=",.0f", title="licitações")
    if log:
        lo, hi = int(np.floor(ini)), int(np.ceil(fim))
        passo = 2 if hi - lo > 6 else 1
        fig.update_xaxes(tickvals=list(range(lo, hi + 1, passo)), ticktext=[_rotulo_pot(v) for v in range(lo, hi + 1, passo)],
                         title=rotulo + " · escala log", tickangle=0)
    else:
        sufixo = f" (≥ {fmt_br(corte_sup, 0)} agrupados no fim)" if corte_sup else ""
        sufixo += f" (≤ {fmt_br(corte_inf, 0)} agrupados no início)" if corte_inf is not None else ""
        fig.update_xaxes(title=rotulo + sufixo)
    if linha_media:
        series = ([(ref, COR_POP, "média pop.")] if ref is not None else []) +                  [(x, COR_AMO if ref is not None else TINTA, "média amostra" if ref is not None else "média")]
        for i, (s, c, nome) in enumerate(series):
            m = s.dropna().astype(float).mean()
            xm = np.log10(m) if log else m
            fig.add_vline(x=xm, line=dict(color=c, width=2))
            fig.add_annotation(x=xm, y=1 - 0.09 * i, yref="paper", text=f" {nome}: {fmt_br(m)}", showarrow=False,
                               yanchor="top", xanchor="left", font=dict(color=TINTA_2, size=11))
    fig.update_xaxes(showgrid=False)
    fig.update_layout(barmode="overlay", showlegend=ref is not None, bargap=0)
    return fig


def fmt_br(v, casas=1):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _rotulo_pot(v: int) -> str:
    n = 10 ** v
    for lim, suf in [(1e9, " bi"), (1e6, " mi"), (1e3, " mil")]:
        if n >= lim:
            return f"{n / lim:,.0f}{suf}"
    return f"{n:,.0f}" if n >= 1 else f"{n:g}".replace(".", ",")


def _rotulo_pot_cont(v: float) -> str:
    n = 10 ** v
    for lim, suf in [(1e9, " bi"), (1e6, " mi"), (1e3, " mil")]:
        if n >= lim:
            return "≈ " + fmt_br(n / lim, 1) + suf
    return "≈ " + fmt_br(n, 2 if n < 10 else 0)


def _resumo_box(v: np.ndarray) -> dict:
    q1, med, q3 = np.quantile(v, [0.25, 0.5, 0.75])
    iqr = q3 - q1
    return dict(q1=[q1], median=[med], q3=[q3], mean=[v.mean()],
                lowerfence=[max(v.min(), q1 - 1.5 * iqr)], upperfence=[min(v.max(), q3 + 1.5 * iqr)])


def box_por_grupo(df: pd.DataFrame, col: str, grupo: str, ordem: list[str], rotulo: str, log: bool = False,
                  ref: pd.DataFrame | None = None) -> go.Figure:
    """Boxplot horizontal por categoria a partir dos quartis (bigodes de Tukey, 1,5 IQR; losango = média)."""
    fig = go.Figure()
    bases = [(ref, "População", COR_POP), (df, "Amostra", COR_AMO)] if ref is not None else [(df, None, None)]
    cores = cores_categorias(ordem)
    todos = []
    for d, nome, cor in bases:
        dd = d[[grupo, col]].dropna()
        dd = dd[dd[col] > 0] if log else dd
        for g in [o for o in ordem if o in set(dd[grupo])]:
            v = dd.loc[dd[grupo] == g, col].astype(float).to_numpy()
            v = np.log10(v) if log else v
            todos.append(v)
            c = cor or cores[g]
            fig.add_box(y=[g], name=nome or g, orientation="h", **_resumo_box(v), boxmean=True,
                        marker=dict(color=c), line=dict(width=1.6, color=c), fillcolor=c + "33",
                        legendgroup=nome or g, showlegend=bool(nome) and g == next(o for o in ordem if o in set(dd[grupo])),
                        offsetgroup=nome, hoverinfo="skip")
    if log and todos:
        allv = np.concatenate(todos)
        lo, hi = int(np.floor(allv.min())), int(np.ceil(allv.max()))
        fig.update_xaxes(tickvals=list(range(lo, hi + 1)), ticktext=[_rotulo_pot(v) for v in range(lo, hi + 1)], tickangle=0)
    fig.update_xaxes(title=rotulo + (" · escala log" if log else ""))
    fig.update_yaxes(autorange="reversed", title=None, showgrid=False)
    fig.update_layout(boxmode="group" if ref is not None else "overlay", showlegend=ref is not None)
    return fig


def curva_concentracao(x: pd.Series, ref: pd.Series | None = None) -> go.Figure:
    """Curva de Pareto: % do valor total acumulado ao somar as licitações da maior para a menor."""
    fig = go.Figure()
    for s, nome, cor in ([(ref, "População", COR_POP)] if ref is not None else []) + [(x, "Amostra" if ref is not None else "Licitações", COR_AMO if ref is not None else COR_POP)]:
        v = np.sort(s.dropna().astype(float).to_numpy())[::-1]
        acum = np.cumsum(v) / v.sum()
        frac = np.arange(1, len(v) + 1) / len(v)
        idx = np.unique(np.geomspace(1, len(v), 400).astype(int)) - 1
        fig.add_scatter(x=frac[idx], y=acum[idx], name=nome, mode="lines", line=dict(color=cor, width=2.5),
                        hovertemplate="as %{x:.2%} maiores<br>somam %{y:.1%} do valor<extra></extra>")
    v = np.sort((ref if ref is not None else x).dropna().astype(float).to_numpy())[::-1]
    acum = np.cumsum(v) / v.sum()
    for fr in (0.01, 0.10):
        y = acum[max(0, int(len(v) * fr) - 1)]
        fig.add_scatter(x=[fr], y=[y], mode="markers+text", showlegend=False, hoverinfo="skip",
                        marker=dict(size=10, color=TINTA, line=dict(color="#fcfcfb", width=2)),
                        text=[f"  {fr:.0%} maiores → {y:.0%} do valor".replace(".", ",")], textposition="middle left",
                        textfont=dict(color=TINTA, size=12))
    fig.update_xaxes(type="log", tickformat=".1%", title="fração das licitações, das maiores para as menores (escala log)",
                     tickvals=[0.0001, 0.001, 0.01, 0.1, 1], ticktext=["0,01%", "0,1%", "1%", "10%", "100%"])
    fig.update_yaxes(tickformat=".0%", range=[0, 1.02], title="% do valor total acumulado")
    return fig


# ----------------------------------------------------------------------------- comparação amostra × população
def dot_diferencas(dif: pd.DataFrame) -> go.Figure:
    """Diferença amostra − população (p.p.) por categoria, com a faixa de ±1,96 erro-padrão esperada numa AAS."""
    d = dif.iloc[::-1]
    fig = go.Figure()
    fig.add_bar(y=d["rotulo"], x=2 * d["faixa"], base=-d["faixa"], orientation="h", name="variação esperada (±1,96 EP)",
                marker=dict(color="#e7e6e1"), hoverinfo="skip", width=0.55)
    cor = np.where(d["fora"], "#d03b3b", COR_AMO)
    fig.add_scatter(y=d["rotulo"], x=d["dif"], mode="markers", name="diferença observada",
                    marker=dict(size=10, color=cor, line=dict(color="#fcfcfb", width=2)),
                    customdata=np.stack([d["p_amo"], d["p_pop"]], axis=1),
                    hovertemplate="%{y}<br>diferença: %{x:+.2f} p.p.<br>amostra %{customdata[0]:.2%} · população %{customdata[1]:.2%}<extra></extra>")
    fig.add_vline(x=0, line=dict(color=TINTA_2, width=1))
    lim = max(d["faixa"].max(), d["dif"].abs().max()) * 1.15
    fig.update_xaxes(range=[-lim, lim], title="amostra − população (pontos percentuais)", zeroline=False)
    fig.update_yaxes(title=None, showgrid=False, tickfont=dict(size=11))
    fig.update_xaxes(title=None)
    fig.update_layout(barmode="overlay")
    return fig


def barras_pvalor(t: pd.DataFrame, alfa: float = 0.05) -> go.Figure:
    d = t.iloc[::-1]
    cor = np.where(d["valor_p"] < alfa, "#d03b3b", COR_POP)
    fig = go.Figure(go.Bar(y=d["Variável"], x=d["valor_p"], orientation="h", marker=dict(color=cor, cornerradius=4),
                           text=[f"{p:.3f}".replace(".", ",") for p in d["valor_p"]], textposition="outside", cliponaxis=False,
                           customdata=d["Teste"], hovertemplate="%{y}<br>%{customdata}<br>valor-p %{x:.4f}<extra></extra>"))
    fig.add_vline(x=alfa, line=dict(color="#d03b3b", width=1.5))
    fig.add_annotation(x=alfa, y=1, yref="paper", text=f"α = {alfa:.0%}", showarrow=False, yanchor="bottom",
                       xanchor="left", font=dict(color="#d03b3b", size=11))
    fig.update_xaxes(range=[0, 1.2], title="valor-p (acima de α: compatível com a população)")
    fig.update_yaxes(title=None, showgrid=False)
    return fig


# ----------------------------------------------------------------------------- inferência
def grafico_ic(est: float, ic: tuple[float, float], param: float, h0: float, pct: bool, nome: str = "Amostra") -> go.Figure:
    fmt = ".2%" if pct else ",.2f"
    fig = go.Figure()
    fig.add_vline(x=h0, line=dict(color=NEUTRA, width=1.5))
    fig.add_annotation(x=h0, y=1.0, yref="paper", text="valor de H₀", showarrow=False, yanchor="bottom",
                       font=dict(color=MUDO, size=11))
    fig.add_scatter(x=[est], y=[nome], mode="markers", name="Estimativa e IC",
                    marker=dict(color=COR_AMO, size=13, line=dict(color="#fcfcfb", width=2)),
                    error_x=dict(type="data", symmetric=False, array=[ic[1] - est], arrayminus=[est - ic[0]],
                                 color=COR_AMO, thickness=2.5, width=10),
                    hovertemplate=f"Estimativa: %{{x:{fmt}}}<extra></extra>")
    fig.add_scatter(x=[param], y=["População"], mode="markers", name="Parâmetro populacional",
                    marker=dict(color=COR_POP, size=13, symbol="diamond", line=dict(color="#fcfcfb", width=2)),
                    hovertemplate=f"Parâmetro: %{{x:{fmt}}}<extra></extra>")
    fig.update_xaxes(tickformat=".1%" if pct else ",.1f")
    fig.update_yaxes(title=None, categoryorder="array", categoryarray=["População", nome], showgrid=False)
    fig.update_layout(legend=dict(y=-0.3, yanchor="top"))
    return fig


def grafico_distribuicao_h0(estat: float, alternativa: str, alfa: float, gl: float | None) -> go.Figure:
    """Densidade da estatística de teste sob H₀ com a região crítica sombreada e a estatística observada."""
    from scipy import stats
    dist = stats.t(gl) if gl else stats.norm()
    lim = max(4.0, abs(estat) * 1.1)
    xs = np.linspace(-lim, lim, 600)
    ys = dist.pdf(xs)
    if alternativa == "greater":
        crit = [dist.ppf(1 - alfa)]; reg = xs >= crit[0]
    elif alternativa == "less":
        crit = [dist.ppf(alfa)]; reg = xs <= crit[0]
    else:
        c = dist.ppf(1 - alfa / 2); crit = [-c, c]; reg = np.abs(xs) >= c
    nome = "t" if gl else "z"
    fig = go.Figure()
    fig.add_scatter(x=xs, y=ys, mode="lines", line=dict(color=TINTA_2, width=2), name=f"distribuição de {nome} sob H₀",
                    hoverinfo="skip")
    for lado in ([xs <= crit[0]] if alternativa == "less" else [xs >= crit[-1]] if alternativa == "greater"
                 else [xs <= crit[0], xs >= crit[1]]):
        fig.add_scatter(x=xs[lado], y=ys[lado], mode="lines", fill="tozeroy", line=dict(color="#d03b3b", width=0),
                        fillcolor="rgba(208,59,59,0.35)", name=f"região crítica (α = {alfa:.0%})", showlegend=bool(lado[-1]) or alternativa == "less",
                        hoverinfo="skip")
    for c in crit:
        fig.add_annotation(x=c, y=float(dist.pdf(c)), text=f"crítico {c:+.2f}".replace(".", ","), showarrow=True,
                           arrowhead=0, ax=0, ay=-28, arrowcolor="#d03b3b", font=dict(color="#d03b3b", size=11))
    fig.add_vline(x=max(min(estat, lim), -lim), line=dict(color=COR_AMO, width=2.5))
    fig.add_annotation(x=max(min(estat, lim), -lim), y=1, yref="paper",
                       text=f"{nome} observado = {estat:.2f}".replace(".", ","), showarrow=False, yanchor="bottom",
                       xanchor="right" if estat > 0 else "left", font=dict(color=TINTA, size=12))
    fig.update_xaxes(title=None, zeroline=False)
    fig.update_yaxes(title=None, showticklabels=False, showgrid=False, rangemode="tozero")
    fig.update_layout(legend=dict(y=-0.12, yanchor="top"), showlegend=True)
    return fig


def tamanho_vs_margem(N: int, conf: float, p: float, margem_escolhida: float, func) -> go.Figure:
    ms = np.linspace(0.01, 0.06, 101)
    ns = [func(N, conf, m, p)["n"] for m in ms]
    n_esc = func(N, conf, margem_escolhida, p)["n"]
    fig = go.Figure()
    fig.add_scatter(x=ms, y=ns, mode="lines", line=dict(color=COR_POP, width=2.5), name="n necessário",
                    hovertemplate="margem %{x:.2%}<br>n = %{y:,.0f}<extra></extra>")
    fig.add_scatter(x=[margem_escolhida], y=[n_esc], mode="markers+text", name="escolha do trabalho",
                    marker=dict(color=COR_AMO, size=12, line=dict(color="#fcfcfb", width=2)),
                    text=[f"  E = {margem_escolhida:.1%} → n = {n_esc:,}".replace(",", ".").replace(".0%", "%")],
                    textposition="middle right", textfont=dict(color=TINTA, size=12), hoverinfo="skip")
    for m in [0.05]:
        nm = func(N, conf, m, p)["n"]
        fig.add_annotation(x=m, y=nm, text=f"E = 5% → n = {nm}", showarrow=True, arrowhead=0, ax=0, ay=-35,
                           font=dict(color=MUDO, size=11), arrowcolor=EIXO)
    fig.update_xaxes(tickformat=".0%", title="margem de erro (E)")
    fig.update_yaxes(type="log", title="tamanho da amostra (escala log)", tickvals=[200, 500, 1000, 2000, 5000, 10000],
                     ticktext=["200", "500", "1.000", "2.000", "5.000", "10.000"], minor=dict(showgrid=False))
    fig.update_layout(showlegend=False)
    return fig
