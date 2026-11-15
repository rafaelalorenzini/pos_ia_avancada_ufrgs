"""Checagens: fórmulas contra referências, resultados da amostra oficial e todas as páginas do app sem exceção.

Uso:  uv run python testes.py
"""
import math
import time

import numpy as np
import pandas as pd
from scipy import stats
from streamlit.testing.v1 import AppTest

from estatistica import (aderencia_qualitativa, aderencia_quantitativa, inferir_media, inferir_proporcao,
                         tamanho_amostra)

# --- tamanho de amostra: casos clássicos
assert tamanho_amostra(10**9, 0.95, 0.05)["n"] == 385
assert tamanho_amostra(1000, 0.95, 0.05)["n"] == 278

# --- proporção: 60 sucessos em 100, H0 p = 0,5 → z = 2
r = inferir_proporcao([True] * 60 + [False] * 40, 0.5, "greater", 0.05, 0.95)
assert math.isclose(r.estatistica, 2.0) and math.isclose(r.p_valor, stats.norm.sf(2.0))

# --- média: confere com scipy
x = np.random.default_rng(0).normal(10, 2, 200)
r = inferir_media(x, 9.5, "two-sided", 0.05, 0.95)
ref = stats.ttest_1samp(x, 9.5)
assert math.isclose(r.estatistica, ref.statistic) and math.isclose(r.p_valor, ref.pvalue)
lo, hi = stats.t.interval(0.95, len(x) - 1, loc=x.mean(), scale=stats.sem(x))
assert math.isclose(r.ic[0], lo) and math.isclose(r.ic[1], hi)

# --- aderência: amostra da própria população não deve rejeitar; amostra viesada deve
rng = np.random.default_rng(1)
popq = pd.Series(rng.choice(list("abc"), 100_000, p=[.5, .3, .2]))
assert aderencia_qualitativa(popq.sample(2000, random_state=2), popq)["p_valor"] > 0.01
assert aderencia_qualitativa(pd.Series(["a"] * 1500 + ["b"] * 500), popq)["p_valor"] < 1e-6
popn = pd.Series(rng.lognormal(0, 1, 100_000))
assert aderencia_quantitativa(popn.sample(2000, random_state=3), popn)["p_valor"] > 0.01
assert aderencia_quantitativa(popn.sample(2000, random_state=3) * 1.5, popn)["p_valor"] < 1e-6
print("fórmulas ok")

# --- resultados da amostra oficial (os do README)
amo = pd.read_parquet("data/amostra.parquet")
assert len(amo) == 2383
assert round(amo["DISPENSA"].mean() * 100, 2) == 54.64
assert round(amo["TEM_CONTRATO"].mean() * 100, 2) == 41.08
assert round(amo["N_LICITANTES"].mean(), 2) == 8.70
assert round(amo["DESCONTO_PCT"].mean(), 2) == 22.31
print("resultados da amostra oficial ok")

# --- app: cada página roda sem exceção
PAGINAS = ["paginas/base.py", "paginas/populacao.py", "paginas/amostra.py", "paginas/inferencia.py"]
for pagina in PAGINAS:
    t0 = time.time()
    at = AppTest.from_file("app.py", default_timeout=300)
    at.run()
    at.switch_page(pagina).run()
    assert not at.exception, (pagina, [e.value for e in at.exception])
    print(f"página ok: {pagina} ({time.time() - t0:.1f}s)")

# --- interações: amostra personalizada, troca de variáveis, métricas do mapa, α e hipótese simulada
at = AppTest.from_file("app.py", default_timeout=300)
at.run()
at.switch_page("paginas/amostra.py").run()
at.sidebar.toggle[0].set_value(True).run()
assert not at.exception, [e.value for e in at.exception]
for v in ["TEM_ADITIVO", "MESORREGIAO", "ANO"]:
    at.selectbox(key="q_Amostra").set_value(v).run()
for v in ["VL_CONTRATADO", "DESCONTO_PCT", "PRAZO_VIGENCIA_DIAS", "N_CONTRATOS"]:
    at.selectbox(key="n_Amostra").set_value(v).run()
assert not at.exception, [e.value for e in at.exception]

at = AppTest.from_file("app.py", default_timeout=300)
at.run()
at.switch_page("paginas/populacao.py").run()
for m in ["Habitantes", "Total de licitações", "% por dispensa"]:
    at.button_group(key="metrica_população").set_value(m).run()
    assert not at.exception, (m, [e.value for e in at.exception])

at = AppTest.from_file("app.py", default_timeout=300)
at.run()
at.switch_page("paginas/inferencia.py").run()
at.button_group(key="alfa").set_value(0.01).run()
for hsel in ["P1", "P2", "M1"]:
    at.radio(key="hsim").set_value(hsel).run()
assert not at.exception, [e.value for e in at.exception]
print("interações ok")
