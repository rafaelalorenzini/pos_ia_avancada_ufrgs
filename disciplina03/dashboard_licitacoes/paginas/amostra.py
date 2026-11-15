import numpy as np
import pandas as pd
import streamlit as st

import graficos as g
from comum import QUALI, QUANTI, contexto, fmt_num, fmt_p, fmt_pct, frequencias, hero, leitura, secao
from estatistica import aderencia_qualitativa, aderencia_quantitativa
from paginas.descritiva import painel

CURTO = {"MODALIDADE_GRUPO": "Modalidade", "OBJETO": "Objeto", "TIPO_ORGAO": "Órgão", "NATUREZA": "Natureza",
         "MESORREGIAO": "Mesorregião", "ANO": "Ano", "PERMITE_CONSORCIO": "Consórcio", "TEM_CONTRATO": "Contrato",
         "TEM_ADITIVO": "Aditivo"}


@st.cache_data(show_spinner=False)
def diferencas(_pop, _amo, chave: str) -> pd.DataFrame:
    N, linhas = len(_pop), []
    for col in QUALI:
        fp, fa = frequencias(_pop, col), frequencias(_amo, col)
        n = int(fa["Frequência"].sum())
        cats = ["Sim"] if set(fp.index) <= {"Sim", "Não"} else list(fp.index)
        for c in cats:
            p = fp.loc[c, "Proporção"]
            pa = fa["Proporção"].get(c, 0.0)
            faixa = 1.96 * np.sqrt(p * (1 - p) / n * (1 - n / N)) * 100
            rot = c.replace(" (Estado, autarquias, consórcios…)", "").replace(" Rio-grandense", "").replace("Metropolitana de ", "Metrop. ")
            linhas.append(dict(rotulo=f"{CURTO[col]} · {rot}", p_pop=p, p_amo=pa, dif=(pa - p) * 100, faixa=faixa,
                               fora=abs(pa - p) * 100 > faixa))
    return pd.DataFrame(linhas)


@st.cache_data(show_spinner=False)
def aderencia(_pop, _amo, chave: str) -> pd.DataFrame:
    linhas = []
    for col, nome in QUALI.items():
        r = aderencia_qualitativa(_amo[col].astype(str).where(_amo[col].notna()), _pop[col].astype(str).where(_pop[col].notna()))
        linhas.append({"Variável": nome, "Tipo": "qualitativa", **r})
    for col, nome in QUANTI.items():
        r = aderencia_quantitativa(_amo[col], _pop[col])
        linhas.append({"Variável": nome, "Tipo": "quantitativa", **r})
    t = pd.DataFrame(linhas).rename(columns={"teste": "Teste", "p_valor": "valor_p"})
    return t


ctx = contexto()
pop, amo = ctx["pop"], ctx["amostra"]
chave = f"{len(amo)}-{ctx['semente']}-{ctx['personalizar']}"

hero("Painel 2 · Amostra", "Análise descritiva da amostra",
     f"As mesmas análises do Painel 1, calculadas só com as <b>{fmt_num(len(amo), 0)} licitações sorteadas</b> "
     f"(AAS, semente {ctx['semente']}). Em <span style='color:{g.COR_AMO};font-weight:600'>laranja</span> a amostra e em "
     f"<span style='color:{g.COR_POP};font-weight:600'>azul</span> a população, só como referência para enxergar as diferenças.",
     g.COR_AMO)

def secao_aderencia():
    secao("00", "A amostra representa a população?",
          "Diferença de cada proporção e testes de aderência de todas as variáveis, antes de entrar nos detalhes.")
    dif = diferencas(pop, amo, chave)
    ad = aderencia(pop, amo, chave)
    c1, c2 = st.columns([1.15, 1], gap="medium")
    with c1, st.container(border=True):
        g.mostrar(g.dot_diferencas(dif), "dif_pp", 140 + 22 * len(dif), "Amostra − população, por categoria (p.p.)")
        fora = dif[dif["fora"]]
        leitura(f"A faixa cinza é a variação que uma AAS desse tamanho produz em 95% dos sorteios (±1,96 erro-padrão, com correção "
                f"para população finita). **{len(dif) - len(fora)} de {len(dif)} categorias** ficam dentro dela"
                + (f"; as que saem ({', '.join(fora['rotulo'])}) são o esperado por acaso, já que ~5% das categorias saem "
                   "mesmo numa amostra perfeita." if len(fora) else ".") + " A maior diferença é de "
                f"{fmt_num(dif['dif'].abs().max(), 1)} p.p.")
    with c2, st.container(border=True):
        g.mostrar(g.barras_pvalor(ad), "aderencia", 140 + 26 * len(ad), "Testes de aderência (valor-p)")
        rej = ad[ad["valor_p"] < 0.05]
        leitura("Qui-quadrado nas qualitativas e Kolmogorov-Smirnov nas quantitativas. H₀: a amostra vem da mesma distribuição "
                f"da população. **{len(ad) - len(rej)} de {len(ad)} variáveis** não rejeitam H₀ a 5%"
                + (f"; {', '.join(rej['Variável'])} rejeitam, o que, com {len(ad)} testes, está dentro do esperado só por acaso (erro tipo I)."
                   if len(rej) else ": nenhuma evidência de que a amostra seja diferente da população.")
                + " Em variáveis discretas (contagens, dias) o KS é conservador.")
        with st.expander("Ver tabela dos testes"):
            t = ad.assign(Estatística=ad["estatistica"].map(lambda v: fmt_num(v, 3)),
                          **{"Valor-p": ad["valor_p"].map(fmt_p), "n (amostra)": ad["n"].map(lambda v: fmt_num(v, 0)),
                             "Decisão (α = 5%)": np.where(ad["valor_p"] < 0.05, "Rejeita H₀", "Não rejeita H₀")})
            st.dataframe(t[["Variável", "Teste", "Estatística", "Valor-p", "n (amostra)", "Decisão (α = 5%)"]], hide_index=True,
                         width="stretch")


painel(amo, pop, "Amostra", ctx, extra=secao_aderencia)
