import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from scipy import stats

import graficos as g
from comum import carregar, chip, contexto, fmt_num, fmt_p, fmt_pct, hero, leitura, secao
from estatistica import ALTERNATIVAS, ic_bootstrap_media, inferir_media, inferir_proporcao, simular

HIPOTESES = [
    dict(id="P1", tipo="proporção", col="DISPENSA", h0=0.5, alt="greater",
         titulo="A maioria das contratações é feita por dispensa de licitação?",
         variavel="Modalidade (qualitativa nominal)",
         evento="licitação na modalidade **dispensa** (art. 75 da Lei 14.133: PRD e dispensa eletrônica PDE)",
         justificativa="A Lei 14.133/2021 trata a licitação como regra e a dispensa como exceção. "
                       "Testamos se a exceção já é a maioria dos processos registrados no LicitaCon.",
         rotulo_param="p = proporção de dispensas", unid="das licitações são dispensas"),
    dict(id="P2", tipo="proporção", col="TEM_CONTRATO", h0=0.5, alt="less",
         titulo="Menos da metade das licitações gera contrato registrado?",
         variavel="Gerou contrato registrado (qualitativa binária)",
         evento="licitação com **ao menos um contrato** no conjunto de contratos do TCE-RS (2025–2026)",
         justificativa="Liga as duas bases. Se menos da metade das licitações tem contrato registrado, as análises de "
                       "execução (fornecedor, aditivos, vigência) cobrem só parte do universo. A lei permite trocar o "
                       "contrato por nota de empenho em compras pequenas (art. 95).",
         rotulo_param="p = proporção com contrato", unid="das licitações geraram contrato"),
    dict(id="M1", tipo="média", col="N_LICITANTES", h0=3.0, alt="greater",
         titulo="Pregões e concorrências atraem, em média, mais de 3 licitantes?",
         variavel="Nº de licitantes (quantitativa discreta)",
         evento="número de licitantes distintos por licitação de **pregão ou concorrência** (licitante.csv)",
         justificativa="Três propostas é a referência tradicional de competição mínima (era a exigência do convite na "
                       "Lei 8.666, art. 22 §3º). Média acima de 3 indica disputa efetiva nas modalidades competitivas.",
         rotulo_param="μ = média de licitantes", unid="licitantes por disputa, em média"),
    dict(id="M2", tipo="média", col="DESCONTO_PCT", h0=20.0, alt="two-sided",
         titulo="O desconto médio obtido em pregões e concorrências é de 20%?",
         variavel="Desconto homologado, % (quantitativa contínua)",
         evento="desconto = 1 − homologado ÷ estimado (%), em **pregão ou concorrência** com os dois valores válidos",
         justificativa="Mede a economia do processo competitivo sobre o orçamento estimado. 20% é um patamar redondo de "
                       "referência; o teste é bilateral porque não há expectativa prévia de direção.",
         rotulo_param="μ = desconto médio (%)", unid="de desconto médio"),
]
NOME_ALT = {"greater": "unilateral à direita", "less": "unilateral à esquerda", "two-sided": "bilateral"}
SINAL_H0 = {"greater": "≤", "less": "≥", "two-sided": "="}
LATEX_H0 = {"greater": r"\le", "less": r"\ge", "two-sided": "="}
LATEX_H1 = {"greater": ">", "less": "<", "two-sided": r"\ne"}


def tex(v, casas=4):
    return f"{v:.{casas}f}".replace(".", "{,}")


def h0_verdadeira(param, h):
    if h["alt"] == "greater":
        return param <= h["h0"]
    if h["alt"] == "less":
        return param >= h["h0"]
    return bool(np.isclose(param, h["h0"]))


def ic_wilson(phat, n, conf):
    z = stats.norm.ppf(1 - (1 - conf) / 2)
    c = (phat + z * z / (2 * n)) / (1 + z * z / n)
    m = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - m, c + m


def calcular(h, amo, pop, alfa, conf):
    if h["tipo"] == "proporção":
        r = inferir_proporcao(amo[h["col"]], h["h0"], h["alt"], alfa, conf)
        param = pop[h["col"]].dropna().astype(bool).mean()
    else:
        r = inferir_media(amo[h["col"]], h["h0"], h["alt"], alfa, conf)
        param = pop[h["col"]].dropna().astype(float).mean()
    return r, param


def bloco(h, r, param, amo, alfa, conf, N_pop_dom):
    pct = h["tipo"] == "proporção"
    f = (lambda v: fmt_pct(v, 2)) if pct else (lambda v: fmt_num(v, 2))
    simb = "p" if pct else "μ"
    lsimb = "p" if pct else r"\mu"
    v0 = f(h["h0"])
    verdade = h0_verdadeira(param, h)
    cobre = r.ic[0] <= param <= r.ic[1]

    st.markdown(f"### {h['id']} · {h['titulo']}")
    st.markdown(chip(h["tipo"].capitalize()) + chip(NOME_ALT[h["alt"]]) + chip(f"α = {fmt_pct(alfa, 0)}") +
                chip("Rejeita H₀" if r.rejeita_h0 else "Não rejeita H₀", "ok" if r.rejeita_h0 else "alerta"),
                unsafe_allow_html=True)

    esq, dir_ = st.columns([1.05, 1], gap="large")
    with esq:
        with st.container(border=True):
            st.markdown(f"**Variável:** {h['variavel']}  \n**Evento / medida:** {h['evento']}  \n"
                        f"**Por que esta pergunta:** {h['justificativa']}")
            st.latex(rf"H_0:\ {lsimb} {LATEX_H0[h['alt']]} {tex(h['h0'], 2)} \qquad H_1:\ {lsimb} {LATEX_H1[h['alt']]} {tex(h['h0'], 2)}")
        m = st.columns(4)
        m[0].metric("n no domínio", fmt_num(r.n, 0), border=True)
        m[1].metric("Estimativa " + ("p̂" if pct else "x̄"), f(r.estimativa), border=True)
        m[2].metric(f"Estatística {r.nome_estatistica}", fmt_num(r.estatistica, 2), border=True)
        m[3].metric("Valor-p", fmt_p(r.p_valor), border=True)

        with st.container(border=True):
            st.markdown("**Cálculo com os dados da amostra**")
            n = r.n
            if pct:
                st.latex(rf"z = \frac{{\hat p - p_0}}{{\sqrt{{p_0(1-p_0)/n}}}} = \frac{{{tex(r.estimativa)} - {tex(h['h0'], 2)}}}"
                         rf"{{\sqrt{{{tex(h['h0'], 2)}\cdot{tex(1 - h['h0'], 2)}/{n}}}}} = {tex(r.estatistica, 3)}")
                zc = stats.norm.ppf(1 - (1 - conf) / 2)
                st.latex(rf"IC_{{{int(round(conf * 100))}\%}} = \hat p \pm z_{{\alpha/2}}\sqrt{{\frac{{\hat p(1-\hat p)}}{{n}}}}")
                st.latex(rf"= {tex(r.estimativa)} \pm {tex(zc, 3)}\cdot{tex(r.erro_padrao)} = [{tex(r.ic[0])};\ {tex(r.ic[1])}]")
            else:
                s = r.erro_padrao * math.sqrt(n)
                st.latex(rf"t = \frac{{\bar x - \mu_0}}{{s/\sqrt n}} = \frac{{{tex(r.estimativa, 3)} - {tex(h['h0'], 1)}}}"
                         rf"{{{tex(s, 3)}/\sqrt{{{n}}}}} = {tex(r.estatistica, 3)} \quad (gl = {n - 1})")
                tc = stats.t.ppf(1 - (1 - conf) / 2, n - 1)
                st.latex(rf"IC_{{{int(round(conf * 100))}\%}} = \bar x \pm t_{{\alpha/2,\,n-1}}\frac{{s}}{{\sqrt n}}")
                st.latex(rf"= {tex(r.estimativa, 3)} \pm {tex(tc, 3)}\cdot{tex(r.erro_padrao, 3)} = [{tex(r.ic[0], 3)};\ {tex(r.ic[1], 3)}]")
            teste = "teste z para uma proporção (erro-padrão sob H₀ usa p₀)" if pct else "teste t de Student para uma média (σ desconhecido)"
            st.caption(f"Procedimento: {teste}, {NOME_ALT[h['alt']]}. IC {'de Wald' if pct else 't'} bilateral de "
                       f"{fmt_pct(conf, 0)}." + (f" Para um teste unilateral a α = {fmt_pct(alfa, 0)}, a decisão equivale a "
                       f"um IC bilateral de {fmt_pct(1 - 2 * alfa, 0)}." if h["alt"] != "two-sided" else ""))

        with st.container(border=True):
            st.markdown("**Condições de aplicação**")
            linhas = []
            for k, (v, ok) in r.condicoes.items():
                vv = fmt_num(v, 1) if isinstance(v, (int, float, np.floating)) else v
                linhas.append(chip(("✓ " if ok else "! ") + f"{k}: {vv}", "ok" if ok else "alerta"))
            st.markdown(" ".join(linhas), unsafe_allow_html=True)
            if pct:
                wl, wu = ic_wilson(r.estimativa, r.n, conf)
                st.caption(f"Checagem: IC de Wilson = [{f(wl)} ; {f(wu)}], praticamente igual ao de Wald, porque n é grande "
                           "e p̂ está longe de 0 e de 1.")
            else:
                bl, bu = ic_bootstrap_media(amo[h["col"]], conf)
                perto = max(abs(bl - r.ic[0]), abs(bu - r.ic[1])) <= 0.1 * (r.ic[1] - r.ic[0])
                st.caption(f"A variável é assimétrica, mas com n = {r.n} o TCL garante a normalidade aproximada de x̄. "
                           f"Checagem: IC bootstrap percentil = [{f(bl)} ; {f(bu)}], "
                           + ("próximo do IC t." if perto else "diferente do IC t em mais de 10% da largura; o bootstrap é mais confiável aqui."))

    with dir_:
        with st.container(border=True):
            g.mostrar(g.grafico_distribuicao_h0(r.estatistica, h["alt"], alfa, r.gl), f"h0_{h['id']}", 290,
                      f"Onde a estatística observada cai sob H₀")
            st.caption(f"Valor-p = {fmt_p(r.p_valor)}: se H₀ fosse verdadeira, a chance de obter uma estatística tão ou mais "
                       f"extrema que {fmt_num(r.estatistica, 2)} seria de {fmt_pct(r.p_valor, 4) if r.p_valor >= 1e-4 else 'menos de 0,01%'}.")
        with st.container(border=True):
            g.mostrar(g.grafico_ic(r.estimativa, r.ic, param, h["h0"], pct), f"ic_{h['id']}", 230,
                      "Estimativa amostral, IC e parâmetro populacional")
        erro = ""
        if r.rejeita_h0 == verdade:
            erro = (" Isso é um **erro tipo I**: rejeitamos uma H₀ que é verdadeira na população." if r.rejeita_h0 else
                    " Isso é um **erro tipo II**: H₀ é falsa na população, mas a amostra não teve evidência (poder) suficiente "
                    "para rejeitá-la.")
        decisao = (f"Como o valor-p ({fmt_p(r.p_valor)}) é {'menor' if r.rejeita_h0 else 'maior'} que α = {fmt_pct(alfa, 0)}, "
                   f"**{'rejeitamos' if r.rejeita_h0 else 'não rejeitamos'} H₀**. ")
        if pct or h["alt"] != "two-sided":
            sentido = {"greater": "acima de", "less": "abaixo de"}.get(h["alt"], "diferente de")
            decisao += (f"Há evidência de que {simb} está {sentido} {v0}." if r.rejeita_h0
                        else f"Não há evidência suficiente de que {simb} esteja {sentido} {v0}.")
        else:
            decisao += ("Há evidência de que o desconto médio é diferente de 20%." if r.rejeita_h0 else
                        f"Os dados são compatíveis com um desconto médio de 20%: o IC [{f(r.ic[0])} ; {f(r.ic[1])}] contém 20.")
        comp = (f" **Comparando com a população:** o parâmetro real é **{f(param)}** ({fmt_num(N_pop_dom, 0)} licitações no domínio); "
                f"a estimativa errou por {('+' if r.estimativa >= param else '') + (fmt_num((r.estimativa - param) * 100, 2) + ' p.p.' if pct else fmt_num(r.estimativa - param, 2))} "
                f"e o IC {'**contém**' if cobre else '**não contém**'} o parâmetro. Na população, H₀ é "
                f"{'verdadeira' if verdade else 'falsa'}, então a decisão da amostra está "
                f"{'**correta**' if r.rejeita_h0 != verdade else '**errada**'}.{erro}")
        (st.success if (cobre and not erro) else st.warning)(decisao + comp)


def resumo_forest(res):
    fig = make_subplots(rows=1, cols=4, subplot_titles=[f"{h['id']} · {h['rotulo_param']}" for h, _, _ in res],
                        horizontal_spacing=0.07)
    for i, (h, r, param) in enumerate(res, start=1):
        pct = h["tipo"] == "proporção"
        esc = 100 if pct else 1
        fig.add_scatter(x=[r.estimativa * esc], y=["Amostra"], mode="markers", row=1, col=i, showlegend=i == 1,
                        name="estimativa e IC (amostra)", marker=dict(color=g.COR_AMO, size=11, line=dict(color="#fcfcfb", width=2)),
                        error_x=dict(type="data", symmetric=False, array=[(r.ic[1] - r.estimativa) * esc],
                                     arrayminus=[(r.estimativa - r.ic[0]) * esc], color=g.COR_AMO, thickness=2.5, width=8),
                        hovertemplate="%{x:.2f}<extra></extra>")
        fig.add_scatter(x=[param * esc], y=["População"], mode="markers", row=1, col=i, showlegend=i == 1,
                        name="parâmetro populacional", marker=dict(color=g.COR_POP, size=12, symbol="diamond",
                                                                   line=dict(color="#fcfcfb", width=2)),
                        hovertemplate="%{x:.2f}<extra></extra>")
        fig.add_vline(x=h["h0"] * esc, line=dict(color=g.NEUTRA, width=1.5), row=1, col=i)
        fig.update_xaxes(ticksuffix="%" if pct or h["col"] == "DESCONTO_PCT" else "", row=1, col=i)
        fig.update_yaxes(showgrid=False, categoryorder="array", categoryarray=["População", "Amostra"],
                         showticklabels=i == 1, row=1, col=i)
    fig.update_annotations(font=dict(size=12, color=g.TINTA_2))
    fig.update_layout(legend=dict(y=-0.25, yanchor="top"), margin=dict(t=40))
    return fig


@st.cache_data(show_spinner="Simulando amostras…")
def simulacao(col, tipo, h0, alt, alfa, confianca, n, reps):
    p = carregar()[0]
    v = p[col].astype(float).to_numpy() if tipo == "média" else p[col].astype("Float64").to_numpy(dtype=float, na_value=np.nan)
    return simular(v, n, reps, tipo, h0, alt, alfa, confianca, semente=1)


# =============================================================================== página
ctx = contexto()
pop, amo = ctx["pop"], ctx["amostra"]

hero("Painel 3 · Inferência", "Intervalos de confiança, testes de hipóteses e comparação",
     f"Toda a inferência usa <b>só a amostra</b> (n = {fmt_num(len(amo), 0)}). Os parâmetros da população, calculados "
     "diretamente sobre as 305 mil licitações, servem para avaliar se as conclusões da amostra acertaram.", "#1baf7a")

c1, c2 = st.columns([1, 2.4])
alfa = c1.segmented_control("Nível de significância (α)", [0.01, 0.05, 0.10], default=0.05,
                            format_func=lambda v: f"{v:.0%}", key="alfa") or 0.05
conf = 1 - alfa
c2.markdown(f"<div class='leitura'>Os intervalos de confiança usam <b>{fmt_pct(conf, 0)}</b> (coerentes com α). Duas hipóteses "
            "de <b>proporção</b> (teste z) e duas de <b>média</b> (teste t). As de média valem para o domínio de pregões e "
            "concorrências, então o n efetivo é menor que o da amostra.</div>", unsafe_allow_html=True)

res = [(h, *calcular(h, amo, pop, alfa, conf)) for h in HIPOTESES]

secao("01", "As quatro hipóteses", "Uma aba por hipótese: pergunta, H₀ e H₁, cálculo, condições, gráficos e conclusão.")
abas = st.tabs([f"{h['id']} · {'proporção' if h['tipo'] == 'proporção' else 'média'}" for h in HIPOTESES])
for aba, (h, r, param) in zip(abas, res):
    with aba:
        bloco(h, r, param, amo, alfa, conf, pop[h["col"]].notna().sum())

secao("02", "Resumo: população × amostra",
      "Estimativa e IC da amostra (laranja) contra o parâmetro real (azul); a linha cinza é o valor de H₀.")
with st.container(border=True):
    g.mostrar(resumo_forest(res), "forest", 230)
    acertos = sum(r.ic[0] <= p <= r.ic[1] for _, r, p in res)
    certas = sum(r.rejeita_h0 != h0_verdadeira(p, h) for h, r, p in res)
    leitura(f"**{acertos} de 4 intervalos contêm o parâmetro populacional** e **{certas} de 4 decisões** coincidem com a verdade "
            "da população. Os ICs de proporção são estreitos (±2 p.p., a margem do dimensionamento). Os de média são mais largos, "
            "porque usam só o domínio de pregões e concorrências e as variáveis são muito dispersas.")
    f = lambda h, v: fmt_pct(v, 2) if h["tipo"] == "proporção" else fmt_num(v, 2)
    tab = pd.DataFrame([{
        "Hipótese": h["id"], "Parâmetro": h["rotulo_param"],
        "H₀ × H₁": f"{'p' if h['tipo'] == 'proporção' else 'μ'} {SINAL_H0[h['alt']]} {f(h, h['h0'])} × "
                   f"{ALTERNATIVAS[h['alt']]} {f(h, h['h0'])}",
        "n": fmt_num(r.n, 0), "Estimativa": f(h, r.estimativa), f"IC {fmt_pct(conf, 0)}": f"[{f(h, r.ic[0])} ; {f(h, r.ic[1])}]",
        "Estatística": f"{r.nome_estatistica} = {fmt_num(r.estatistica, 2)}", "Valor-p": fmt_p(r.p_valor),
        "Decisão": "Rejeita H₀" if r.rejeita_h0 else "Não rejeita H₀",
        "População": f(h, p), "IC contém?": "Sim" if r.ic[0] <= p <= r.ic[1] else "Não",
        "H₀ na população": "verdadeira" if h0_verdadeira(p, h) else "falsa",
    } for h, r, p in res])
    st.dataframe(tab, hide_index=True, width="stretch")

secao("03", "Efeito da variabilidade amostral",
      "Como temos a população inteira, podemos repetir o sorteio centenas de vezes e ver como estimativas, ICs e decisões variam.")
c1, c2 = st.columns([1, 3], gap="medium")
with c1, st.container(border=True):
    hsel = st.radio("Hipótese", [h["id"] for h in HIPOTESES], horizontal=True, key="hsim")
    reps = st.select_slider("Amostras simuladas", [200, 500, 1000, 2000], value=500, key="reps")
    h, r_of, param = next(t for t in res if t[0]["id"] == hsel)
    sim = simulacao(h["col"], h["tipo"], h["h0"], h["alt"], alfa, conf, len(amo), reps)
    cobertura = ((sim["ic_inf"] <= param) & (sim["ic_sup"] >= param)).mean()
    rejeicao = sim["rejeita_h0"].mean()
    h0v = h0_verdadeira(param, h)
    ff = (lambda v: fmt_pct(v, 2)) if h["tipo"] == "proporção" else (lambda v: fmt_num(v, 2))
    st.metric(f"Cobertura dos ICs (nominal {fmt_pct(conf, 0)})", fmt_pct(cobertura, 1), border=True)
    st.metric("Erro tipo I (H₀ verdadeira)" if h0v else "Poder do teste (rejeita H₀ falsa)", fmt_pct(rejeicao, 1), border=True)
    st.metric("Erro-padrão empírico", ff(sim["estimativa"].std()), border=True)
with c2:
    with st.container(border=True):
        fig = go.Figure()
        hist, bordas = np.histogram(sim["estimativa"], 40)
        fig.add_bar(x=(bordas[:-1] + bordas[1:]) / 2, y=hist, width=np.diff(bordas), name="estimativas simuladas",
                    marker=dict(color=g.COR_AMO, opacity=0.8, line=dict(color="#fcfcfb", width=1)),
                    hovertemplate="%{x:.4f}<br>%{y} amostras<extra></extra>")
        fig.add_vline(x=param, line=dict(color=g.COR_POP, width=2.5))
        fig.add_annotation(x=param, y=1, yref="paper", text="parâmetro", showarrow=False, yanchor="bottom",
                           font=dict(color=g.COR_POP))
        fig.add_vline(x=h["h0"], line=dict(color=g.NEUTRA, width=1.5))
        fig.add_annotation(x=h["h0"], y=0.92, yref="paper", text="H₀", showarrow=False, xanchor="left",
                           font=dict(color=g.MUDO))
        fig.add_vline(x=r_of.estimativa, line=dict(color=g.TINTA, width=1.5))
        fig.add_annotation(x=r_of.estimativa, y=0.82, yref="paper", text=" amostra do trabalho", showarrow=False,
                           xanchor="left", font=dict(color=g.TINTA))
        fig.update_xaxes(title=f"estimativa de {h['rotulo_param']} em {reps} amostras de n = {fmt_num(len(amo), 0)}",
                         tickformat=".1%" if h["tipo"] == "proporção" else None, showgrid=False)
        fig.update_yaxes(title="amostras")
        fig.update_layout(showlegend=False, bargap=0)
        g.mostrar(fig, "sim", 330, f"Distribuição amostral simulada · {hsel}")
    with st.container(border=True):
        ordem = sim.head(80).reset_index(drop=True)
        ordem["cobre"] = (ordem["ic_inf"] <= param) & (ordem["ic_sup"] >= param)
        figc = go.Figure()
        for cob, nome, cor in [(True, "contém o parâmetro", g.EIXO), (False, "não contém", "#d03b3b")]:
            d = ordem[ordem["cobre"] == cob]
            figc.add_scatter(x=d["estimativa"], y=d.index, mode="markers", name=nome, marker=dict(color=cor, size=6),
                             error_x=dict(type="data", symmetric=False, array=d["ic_sup"] - d["estimativa"],
                                          arrayminus=d["estimativa"] - d["ic_inf"], color=cor, thickness=1.4, width=0),
                             hovertemplate="amostra %{y}<br>estimativa %{x}<extra></extra>")
        figc.add_vline(x=param, line=dict(color=g.COR_POP, width=2))
        figc.update_yaxes(title="amostra simulada", showticklabels=False, showgrid=False)
        figc.update_xaxes(tickformat=".1%" if h["tipo"] == "proporção" else None)
        g.mostrar(figc, "ics", 380, "80 primeiros ICs simulados")
leitura(f"Em {reps} sorteios, **{fmt_pct(cobertura, 1)} dos ICs contêm o parâmetro**, perto dos {fmt_pct(conf, 0)} nominais: o "
        "método funciona como prometido. "
        + (f"Como H₀ é falsa na população, a taxa de rejeição ({fmt_pct(rejeicao, 1)}) é o **poder** do teste."
           + (" O poder baixo explica o erro tipo II da amostra do trabalho: o desconto real (≈23%) está perto demais de 20% "
              "para o n disponível no domínio." if hsel == "M2" else "")
           if not h0v else f"Como H₀ é verdadeira, a taxa de rejeição ({fmt_pct(rejeicao, 1)}) é o erro tipo I, próximo de α."))

secao("04", "Limitações")
lim = [
    ("Variabilidade amostral", "A amostra do trabalho é uma entre muitas possíveis. Uma H₀ próxima do valor verdadeiro "
     "(como em M2) pode não ser rejeitada mesmo sendo falsa (erro tipo II), por baixo poder."),
    ("Domínios", "M1 e M2 usam só pregões e concorrências com o dado preenchido. O n efetivo nesses domínios é aleatório e "
     "bem menor que n, o que alarga os ICs. O dimensionamento foi feito para proporções na população toda."),
    ("Qualidade dos dados", "Os dados são autodeclarados pelos órgãos e não foram auditados. Erros grosseiros (ex.: R$ 89 bi "
     "homologado sobre R$ 422 mil estimado) foram anulados por regra, mas erros menores permanecem."),
    ("Recorte temporal", "2026 é parcial, e contratos de licitações recentes ainda serão registrados. Por isso P2 descreve a "
     "situação até o download, não a proporção final."),
    ("Assimetria", "Licitantes e valores são muito assimétricos e a média é sensível a extremos. Com n grande o TCL sustenta "
     "o teste t, e o bootstrap confirma, mas a mediana descreve melhor a licitação típica."),
    ("Inferência × população", "Como temos a população inteira, aqui o teste serve para avaliar o método. Numa situação real "
     "só teríamos a amostra."),
]
cols = st.columns(3, gap="medium")
for i, (t, d) in enumerate(lim):
    with cols[i % 3], st.container(border=True):
        st.markdown(f"**{t}**")
        st.caption(d)
