"""Seções descritivas compartilhadas pelo Painel 1 (população) e pelo Painel 2 (amostra × população)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

import graficos as g
from comum import (ORDEM, QUALI, QUANTI, fmt_medidas, fmt_num, fmt_pct, fmt_rs, frequencias, leitura, medidas,
                   secao, ultimo_mes_completo)

MOD = ORDEM["MODALIDADE_GRUPO"]
ORG = ORDEM["TIPO_ORGAO"]
OBJ = ORDEM["OBJETO"]
COMPET = ["Pregão", "Concorrência"]
METRICAS_MAPA = {
    "Habitantes": ("POP_2022", "habitantes", ",.0f", True),
    "Licitações por 1.000 hab.": ("POR_MIL_HAB", "licitações / 1.000 hab.", ",.1f", False),
    "Total de licitações": ("LICITACOES", "licitações", ",.0f", True),
    "% por dispensa": ("PCT_DISPENSA", "% dispensa", ".1%", False),
}


def _pp(v):
    return ("+" if v >= 0 else "") + fmt_num(v * 100, 1) + " p.p."


def por_municipio(df: pd.DataFrame, mun: pd.DataFrame) -> pd.DataFrame:
    d = df[df["COD_IBGE"].notna()]
    agg = d.groupby("COD_IBGE").agg(LICITACOES=("ID", "size"), PCT_DISPENSA=("DISPENSA", "mean"))
    out = mun.merge(agg, left_on="COD_IBGE", right_index=True, how="left")
    out["LICITACOES"] = out["LICITACOES"].fillna(0)
    out["POR_MIL_HAB"] = out["LICITACOES"] / out["POP_2022"] * 1000
    return out


# =============================================================================== KPIs
def kpis(df: pd.DataFrame, ref: pd.DataFrame | None):
    def val(d):
        return {
            "Licitações": (len(d), lambda v: fmt_num(v, 0), None),
            "Órgãos": (d["CD_ORGAO"].nunique(), lambda v: fmt_num(v, 0), None),
            "Por dispensa": (d["DISPENSA"].mean(), fmt_pct, "pp"),
            "Geraram contrato": (d["TEM_CONTRATO"].mean(), fmt_pct, "pp"),
            "Valor mediano": (d["VL_REF"].median(), fmt_rs, "rs"),
            "Licitantes (média)": (d["N_LICITANTES"].mean(), lambda v: fmt_num(v, 1), "num"),
            "Dias p/ homologar": (d["DIAS_ATE_HOMOLOGACAO"].median(), lambda v: fmt_num(v, 0), "num"),
        }
    atual, base = val(df), (val(ref) if ref is not None else None)
    if base is not None:
        st.caption("Abaixo de cada valor: diferença da amostra em relação à população.")
    cols = st.columns(len(atual))
    for c, (rot, (v, f, tipo)) in zip(cols, atual.items()):
        delta = None
        if base is not None and tipo:
            d = v - base[rot][0]
            delta = _pp(d) if tipo == "pp" else ("+" if d >= 0 else "−") + fmt_rs(abs(d)).replace("R$ ", "") if tipo == "rs"                 else ("+" if d >= 0 else "") + fmt_num(d, 1)
        c.metric(rot, f(v), delta, delta_color="off", border=True)


# =============================================================================== seções
def perfil(df, ref, k):
    secao("01", "Perfil das contratações", "Como as compras públicas se dividem por modalidade, objeto e tipo de órgão.")
    f = frequencias(df, "MODALIDADE_GRUPO")
    fr = frequencias(ref, "MODALIDADE_GRUPO") if ref is not None else None
    c1, c2 = st.columns([1, 1.25], gap="medium")
    with c1, st.container(border=True):
        g.mostrar(g.barras_freq(f, fr, "Modalidade"), f"mod_{k}", 330, "Licitações por modalidade")
        disp, inex = f.loc["Dispensa", "Proporção"], f.loc["Inexigibilidade", "Proporção"]
        leitura(f"**{fmt_pct(disp + inex)}** dos processos são contratação direta (dispensa {fmt_pct(disp)} + "
                f"inexigibilidade {fmt_pct(inex)}). Pregão e concorrência, as modalidades com disputa, somam "
                f"{fmt_pct(f.reindex(COMPET)['Proporção'].sum())}.")
    with c2, st.container(border=True):
        g.mostrar(g.treemap(df, "MODALIDADE_GRUPO", "OBJETO", MOD), f"tree_{k}", 330, "Modalidade → tipo de objeto")
        top = df.groupby(["MODALIDADE_GRUPO", "OBJETO"]).size().idxmax()
        obras = df.loc[df["OBJETO"].eq("Obras e serv. de engenharia"), "MODALIDADE_GRUPO"].value_counts(normalize=True)
        leitura(f"A área de cada bloco é a fatia das licitações. O maior bloco é **{top[0]} de {top[1].lower()}**. "
                f"Obras e serviços de engenharia seguem outro padrão: {fmt_pct(obras.get('Concorrência', 0))} vão para "
                "concorrência.")
    c1, c2 = st.columns([1.25, 1], gap="medium")
    with c1, st.container(border=True):
        g.mostrar(g.heatmap_cruzado(df, "TIPO_ORGAO", "MODALIDADE_GRUPO", ORG, MOD, ref), f"heat_{k}", 300,
                  "Modalidade dentro de cada tipo de órgão (% da linha)")
        t = pd.crosstab(df["TIPO_ORGAO"], df["MODALIDADE_GRUPO"], normalize="index")
        leitura(f"Cada linha soma 100%. Nas câmaras de vereadores a dispensa chega a **{fmt_pct(t.loc['Câmara de Vereadores', 'Dispensa'])}**; "
                f"nas prefeituras é {fmt_pct(t.loc['Prefeitura', 'Dispensa'])}. Órgãos estaduais, autarquias e consórcios usam "
                f"mais pregão ({fmt_pct(t.iloc[:, list(t.columns).index('Pregão')].iloc[-1])}).")
    with c2, st.container(border=True):
        fo = frequencias(df, "OBJETO")
        fro = frequencias(ref, "OBJETO") if ref is not None else None
        g.mostrar(g.barras_freq(fo, fro, "Tipo de objeto"), f"obj_{k}", 300, "Licitações por tipo de objeto")
        leitura(f"Compras de bens ({fmt_pct(fo.loc['Compras', 'Proporção'])}) e serviços em geral "
                f"({fmt_pct(fo.loc['Outros serviços', 'Proporção'])}) dominam. Obras são só "
                f"{fmt_pct(fo.loc['Obras e serv. de engenharia', 'Proporção'])} dos processos, mas pesam no valor.")


def tempo(df, ref, k, meta):
    ate = ultimo_mes_completo(meta)
    secao("02", "Ao longo do tempo",
          f"Licitações pela data de abertura, de jan/2025 até {ate.strftime('%m/%Y')} (último mês completo antes do download).")
    with st.container(border=True):
        if ref is None:
            fig = g.serie_mensal(df, "MODALIDADE_GRUPO", MOD, ate)
            g.mostrar(fig, f"serie_{k}", 360, "Licitações abertas por mês e modalidade")
            m = df[(df["MES_ABERTURA"] >= "2025-01-01") & (df["MES_ABERTURA"] <= ate)]["MES_ABERTURA"].value_counts()
            leitura(f"O volume é estável, em torno de **{fmt_num(m.median(), 0)} licitações por mês** (mediana). As quedas em "
                    f"janeiro ({fmt_num(m.get(pd.Timestamp('2025-01-01'), np.nan), 0)} em 2025, "
                    f"{fmt_num(m.get(pd.Timestamp('2026-01-01'), np.nan), 0)} em 2026) acompanham o início do exercício "
                    "orçamentário. A composição por modalidade quase não muda de um mês para outro.")
        else:
            g.mostrar(g.serie_mensal_comparada(df, ref, ate), f"serie_{k}", 340,
                      "Distribuição das licitações por mês (% do período)")
            leitura("Os dois perfis mensais coincidem. As oscilações da amostra (cerca de 100 licitações por mês) ficam "
                    "dentro do que se espera do sorteio, sem um mês sistematicamente acima ou abaixo.")


def territorio(df, ref, k, mun, geo):
    secao("03", "No território",
          "Prefeituras e câmaras ligadas ao município pelo nome (100% casadas com a lista do IBGE); população do Censo 2022.")
    pm = por_municipio(df, mun)
    c1, c2 = st.columns([1.15, 1], gap="medium")
    with c1, st.container(border=True):
        padrao = "Licitações por 1.000 hab." if ref is None else "Total de licitações"
        escolha = st.segmented_control("Métrica do mapa", list(METRICAS_MAPA), default=padrao,
                                       key=f"metrica_{k}", label_visibility="collapsed") or padrao
        col, rot, fmt, log = METRICAS_MAPA[escolha]
        titulo = f"{escolha} por município" + (" (na amostra)" if ref is not None and col != "POP_2022" else "")
        g.mostrar(g.mapa(geo, pm, col, rot, fmt, log), f"mapa_{k}_{col}", 470, titulo)
        if ref is not None and col != "POP_2022":
            leitura(f"Na amostra caem em média só **{fmt_num(pm['LICITACOES'].mean(), 1)} licitações por município** "
                    f"({fmt_pct((pm['LICITACOES'] == 0).mean(), 0)} dos municípios não têm nenhuma sorteada). Por isso o mapa "
                    "municipal da amostra é ruidoso e não deve ser lido município a município; compare com o Painel 1 e com "
                    "as mesorregiões ao lado, onde a amostra acerta.")
        elif col == "POP_2022":
            top = pm.nlargest(1, "POP_2022").iloc[0]
            leitura(f"O RS tem **{fmt_num(pm['POP_2022'].sum(), 0)} habitantes** em 497 municípios. A mediana é de "
                    f"{fmt_num(pm['POP_2022'].median(), 0)} habitantes: a maioria é pequena e fica no norte e no noroeste. "
                    f"{top['MUNICIPIO']} sozinha tem {fmt_num(top['POP_2022'], 0)} (escala de cor em log).")
        elif col == "POR_MIL_HAB":
            alto = pm.nlargest(1, "POR_MIL_HAB").iloc[0]
            leitura(f"A taxa é **maior nos municípios pequenos**: {alto['MUNICIPIO']} chega a {fmt_num(alto['POR_MIL_HAB'], 1)} "
                    f"licitações por 1.000 habitantes, enquanto Porto Alegre tem "
                    f"{fmt_num(pm.loc[pm['MUNICIPIO'].eq('Porto Alegre'), 'POR_MIL_HAB'].iloc[0], 1)}. Todo município, por menor "
                    "que seja, precisa comprar de tudo, então há um custo fixo de processos. Valores tão altos também indicam práticas de "
                    "registro diferentes (fracionar compras em muitos processos pequenos)." +
                    (" Na amostra são só ~5 licitações por município, então a taxa local oscila muito." if ref is not None else ""))
        elif col == "LICITACOES":
            leitura("O total segue o tamanho do município: as regiões metropolitana e da serra concentram os maiores volumes "
                    "(escala de cor em log)." + (" Na amostra, muitos municípios pequenos ficam com 0 ou 1 licitação sorteada." if ref is not None else ""))
        else:
            leitura("A participação da dispensa varia bastante entre municípios vizinhos. Isso indica que depende mais da "
                    "prática de cada órgão do que da região.")
    with c2, st.container(border=True):
        if ref is None:
            fig, elast = g.dispersao_municipios(pm)
            g.mostrar(fig, f"disp_{k}", 470, "Licitações × habitantes, por município")
            leitura(f"Cada ponto é um município. A inclinação de **{fmt_num(elast, 2)}** (menor que 1) mostra que dobrar a "
                    f"população aumenta o número de licitações em só ~{fmt_num((2 ** elast - 1) * 100, 0)}%: os municípios "
                    "pequenos fazem proporcionalmente mais processos.")
        else:
            f = frequencias(df, "MESORREGIAO")
            fr = frequencias(ref, "MESORREGIAO").sort_values("Proporção", ascending=False)
            f = f.reindex(fr.index).fillna(0)
            g.mostrar(g.barras_freq(f, fr, "Mesorregião"), f"meso_{k}", 470, "Licitações municipais por mesorregião")
            leitura("Agregando por mesorregião, a amostra reproduz bem o mapa da população. No nível de município ela é "
                    "esparsa demais, porque não foi desenhada para isso (seria preciso estratificar).")
    if ref is None:
        c1, c2 = st.columns(2, gap="medium")
        with c1, st.container(border=True):
            fm = frequencias(df, "MESORREGIAO").sort_values("Proporção", ascending=False)
            g.mostrar(g.barras_freq(fm, None, "Mesorregião"), f"meso_{k}", 330, "Licitações municipais por mesorregião")
            leitura(f"Noroeste ({fmt_pct(fm.loc['Noroeste Rio-grandense', 'Proporção'])}) supera a região metropolitana "
                    f"({fmt_pct(fm.loc['Metropolitana de Porto Alegre', 'Proporção'])}) por ter muito mais municípios (e câmaras).")
        with c2, st.container(border=True):
            top = df["NM_ORGAO"].value_counts().head(12)
            g.mostrar(g.ranking(top, "licitações"), f"top_{k}", 330, "Órgãos com mais licitações")
            leitura(f"Os 12 maiores somam {fmt_pct(top.sum() / len(df))} dos processos. Entre {fmt_num(df['CD_ORGAO'].nunique(), 0)} "
                    "órgãos não há concentração extrema no número de processos (no valor, sim: veja a próxima seção).")


def valores(df, ref, k):
    secao("04", "Valores", "Valor de referência = homologado quando existe, senão o estimado; erros grosseiros de cadastro anulados.")
    c1, c2 = st.columns(2, gap="medium")
    v = df["VL_REF"]
    with c1, st.container(border=True):
        g.mostrar(g.histograma(v, ref["VL_REF"] if ref is not None else None, "valor (R$)", log=True), f"hval_{k}", 330,
                  "Distribuição do valor de referência")
        leitura(f"Em escala log a distribuição parece um sino, ou seja, é **log-normal**. Mediana de **{fmt_rs(v.median())}**, "
                f"média de {fmt_rs(v.mean())}: a média é {fmt_num(v.mean() / v.median(), 0)} vezes a mediana, puxada por poucos "
                "contratos enormes.")
    with c2, st.container(border=True):
        g.mostrar(g.box_por_grupo(df, "VL_REF", "MODALIDADE_GRUPO", MOD, "valor (R$)", log=True, ref=ref), f"bval_{k}", 330,
                  "Valor por modalidade (caixa = Q1–Q3, traço = mediana)")
        med = df.groupby("MODALIDADE_GRUPO")["VL_REF"].median()
        leitura(f"A mediana da concorrência ({fmt_rs(med['Concorrência'])}) é cerca de "
                f"{fmt_num(med['Concorrência'] / med['Dispensa'], 0)}× a da dispensa ({fmt_rs(med['Dispensa'])}). A dispensa "
                "concentra os processos pequenos, como prevê a lei (art. 75: limites de valor).")
    with st.container(border=True):
        vv = v.dropna().sort_values(ascending=False)
        top1 = vv.head(max(1, len(vv) // 100)).sum() / vv.sum()
        top10 = vv.head(max(1, len(vv) // 10)).sum() / vv.sum()
        g.mostrar(g.curva_concentracao(v, ref["VL_REF"] if ref is not None else None), f"pareto_{k}", 330,
                  "Concentração do valor: quanto do total está nas maiores licitações")
        leitura(f"**1% das licitações concentra {fmt_pct(top1, 0)} do valor total**, e os 10% maiores somam {fmt_pct(top10, 0)}. "
                "É por isso que as médias de valor são instáveis, e que a inferência deste trabalho usa contagens, "
                "proporções e descontos em vez do valor em R$." +
                (" Na amostra a curva fica mais baixa no começo: ela raramente sorteia os poucos contratos gigantes." if ref is not None else ""))


def competicao(df, ref, k):
    secao("05", "Competição e prazo", "Só pregões e concorrências, as modalidades em que há disputa entre fornecedores.")
    c1, c2, c3 = st.columns(3, gap="medium")
    r = (lambda c: ref[c]) if ref is not None else (lambda c: None)
    with c1, st.container(border=True):
        x = df["N_LICITANTES"]
        g.mostrar(g.histograma(x, r("N_LICITANTES"), "licitantes", corte_sup=40, linha_media=True), f"hlic_{k}", 320,
                  "Nº de licitantes por disputa")
        leitura(f"Mediana de **{fmt_num(x.median(), 0)} licitantes** e média de {fmt_num(x.mean(), 1)}. Uma cauda longa de "
                f"pregões com dezenas de participantes (registro de preços com muitos itens) puxa a média; "
                f"{fmt_pct((x.dropna() <= 1).mean())} tiveram um único licitante.")
    with c2, st.container(border=True):
        x = df["DESCONTO_PCT"]
        g.mostrar(g.histograma(x, r("DESCONTO_PCT"), "desconto (%)", linha_media=True, nbins=40, corte_inf=-50), f"hdesc_{k}", 320,
                  "Desconto: homologado vs. estimado")
        leitura(f"Desconto médio de **{fmt_num(x.mean(), 1)}%** (mediana {fmt_num(x.median(), 1)}%). Há um pico em 0%, de "
                f"processos homologados pelo valor estimado ({fmt_pct((x.dropna().abs() < 0.01).mean())}), e valores "
                "negativos quando o homologado supera o estimado.")
    with c3, st.container(border=True):
        g.mostrar(g.box_por_grupo(df, "DIAS_ATE_HOMOLOGACAO", "MODALIDADE_GRUPO", COMPET, "dias", ref=ref), f"bdias_{k}", 320,
                  "Dias da abertura à homologação")
        med = df.groupby("MODALIDADE_GRUPO")["DIAS_ATE_HOMOLOGACAO"].median()
        leitura(f"O pregão homologa em **{fmt_num(med.get('Pregão'), 0)} dias** (mediana); a concorrência leva "
                f"{fmt_num(med.get('Concorrência'), 0)}. O processo competitivo típico é rápido, mas 25% passam de "
                f"{fmt_num(df['DIAS_ATE_HOMOLOGACAO'].quantile(.75), 0)} dias.")


def contratos(df, ref, k):
    secao("06", "Contratos e aditivos", "Cruzamento com o conjunto de contratos do TCE-RS pela chave da licitação.")
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1, st.container(border=True):
        g.mostrar(g.barras_taxa_por_grupo(df, ref, "MODALIDADE_GRUPO", "TEM_CONTRATO", MOD), f"tcon_{k}", 320,
                  "% que gerou contrato, por modalidade")
        t = df.groupby("MODALIDADE_GRUPO")["TEM_CONTRATO"].mean()
        leitura(f"Concorrências viram contrato em **{fmt_pct(t['Concorrência'], 0)}** dos casos; dispensas, em "
                f"{fmt_pct(t['Dispensa'], 0)}. Em compras pequenas a lei permite trocar o contrato pela nota de empenho (art. 95).")
    with c2, st.container(border=True):
        g.mostrar(g.barras_taxa_por_grupo(df, ref, "MODALIDADE_GRUPO", "TEM_ADITIVO", MOD), f"tadi_{k}", 320,
                  "% de contratos com aditivo, por modalidade")
        t = df.groupby("MODALIDADE_GRUPO")["TEM_ADITIVO"].apply(lambda s: s.dropna().astype(bool).mean())
        leitura(f"Entre as licitações com contrato, **{fmt_pct(df['TEM_ADITIVO'].dropna().astype(bool).mean(), 0)}** já têm "
                f"aditivo. A concorrência lidera ({fmt_pct(t['Concorrência'], 0)}): obras longas costumam ser aditadas em prazo e valor.")
    with c3, st.container(border=True):
        x = df["PRAZO_VIGENCIA_DIAS"]
        g.mostrar(g.histograma(x, ref["PRAZO_VIGENCIA_DIAS"] if ref is not None else None, "dias de vigência",
                               corte_sup=1100, nbins=44), f"hvig_{k}", 320, "Prazo de vigência dos contratos")
        leitura(f"Mediana de **{fmt_num(x.median(), 0)} dias**. Há picos em 12 meses (365 dias, o exercício) e em prazos "
                "curtos de entrega única; acima de 1 ano aparecem os serviços continuados.")


def explorar(df, ref, k, nome):
    secao("07", "Explorar variáveis", "Frequências, proporções e medidas descritivas de qualquer variável selecionada.")
    c1, c2 = st.columns(2, gap="medium")
    with c1, st.container(border=True):
        vq = st.selectbox("Variável qualitativa", list(QUALI), format_func=QUALI.get, key=f"q_{nome}")
        f = frequencias(df, vq)
        fr = frequencias(ref, vq) if ref is not None else None
        g.mostrar(g.barras_freq(f, fr, QUALI[vq]), f"gq_{k}", 300 + 18 * len(f))
        tab = f.copy()
        if fr is not None:
            tab["Prop. população"] = fr["Proporção"]
            tab["Dif. (p.p.)"] = (tab["Proporção"] - tab["Prop. população"]) * 100
        fmt = tab.copy().astype(object)
        for c in tab.columns:
            fmt[c] = tab[c].map(lambda v: fmt_num(v, 0) if c == "Frequência" else fmt_num(v, 2) if "p.p." in c else fmt_pct(v, 2))
        st.dataframe(fmt, column_config={"_index": QUALI[vq]}, width="stretch")
    with c2, st.container(border=True):
        a, b = st.columns([2.2, 1], vertical_alignment="bottom")
        vn = a.selectbox("Variável quantitativa", list(QUANTI), format_func=QUANTI.get, key=f"n_{nome}")
        log = b.toggle("Escala log", value=vn in ("VL_REF", "VL_CONTRATADO"), key=f"log_{nome}")
        g.mostrar(g.histograma(df[vn], ref[vn] if ref is not None else None, QUANTI[vn], log=log, linha_media=not log),
                  f"gn_{k}", 300)
        m = medidas(df[vn]).rename(nome).to_frame()
        if ref is not None:
            m.insert(0, "População", medidas(ref[vn]))
            m["Diferença"] = m[nome] - m["População"]
            m.loc["n", "Diferença"] = np.nan
        st.dataframe(fmt_medidas(m), column_config={"_index": "Medida"}, width="stretch")
    with st.container(border=True):
        st.markdown("**Medidas descritivas de todas as variáveis quantitativas**")
        tudo = pd.DataFrame({QUANTI[c]: medidas(df[c]) for c in QUANTI}).T
        st.dataframe(fmt_medidas(tudo.T).T, width="stretch")
        st.caption("Cada variável usa só as licitações em que está definida (ex.: licitantes e desconto só em pregão e "
                   "concorrência; valor contratado e vigência só entre as que têm contrato).")


def painel(df: pd.DataFrame, ref: pd.DataFrame | None, nome: str, ctx: dict, extra=None):
    k = nome.lower()
    kpis(df, ref)
    if extra:
        extra()
    perfil(df, ref, k)
    tempo(df, ref, k, ctx["meta"])
    territorio(df, ref, k, ctx["mun"], ctx["geo"])
    valores(df, ref, k)
    competicao(df, ref, k)
    contratos(df, ref, k)
    explorar(df, ref, k, nome)
