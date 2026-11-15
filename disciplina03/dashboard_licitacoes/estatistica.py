"""Funções de amostragem e inferência usadas pelo dashboard e pelo preparo dos dados.

Tudo aqui é função pura (sem Streamlit), para poder ser testado e reutilizado.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

ALTERNATIVAS = {"two-sided": "≠", "greater": ">", "less": "<"}


# --------------------------------------------------------------------------- amostragem
def tamanho_amostra(N: int, confianca: float, margem: float, p: float = 0.5) -> dict:
    """Tamanho de amostra para estimar uma proporção, com correção para população finita.

    n0 = z² p (1-p) / E²            (população infinita)
    n  = N z² p (1-p) / (E² (N-1) + z² p (1-p))   (população finita, mesma fórmula da calculadora USP/Bauru)
    """
    z = stats.norm.ppf(1 - (1 - confianca) / 2)
    pq = p * (1 - p)
    n0 = z**2 * pq / margem**2
    n = N * z**2 * pq / (margem**2 * (N - 1) + z**2 * pq)
    return {"z": z, "n0": n0, "n_exato": n, "n": math.ceil(n), "fracao": math.ceil(n) / N}


def sortear_aas(pop: pd.DataFrame, n: int, semente: int) -> pd.DataFrame:
    """Amostra aleatória simples SEM reposição: cada subconjunto de tamanho n tem a mesma chance.

    A população precisa estar numa ordem fixa (o preparo ordena pela chave da licitação),
    para que a mesma semente gere sempre a mesma amostra.
    """
    rng = np.random.default_rng(semente)
    idx = rng.choice(len(pop), size=n, replace=False)
    return pop.iloc[np.sort(idx)]


# --------------------------------------------------------------------------- inferência
@dataclass
class Resultado:
    tipo: str               # "proporção" | "média"
    n: int
    estimativa: float       # p̂ ou x̄
    erro_padrao: float
    ic: tuple[float, float]
    confianca: float
    valor_h0: float
    alternativa: str
    estatistica: float      # z ou t
    nome_estatistica: str
    gl: float | None
    p_valor: float
    alfa: float
    condicoes: dict = field(default_factory=dict)

    @property
    def rejeita_h0(self) -> bool:
        return self.p_valor < self.alfa


def _p_valor_normal(z: float, alternativa: str) -> float:
    if alternativa == "greater":
        return stats.norm.sf(z)
    if alternativa == "less":
        return stats.norm.cdf(z)
    return 2 * stats.norm.sf(abs(z))


def inferir_proporcao(x, p0: float, alternativa: str, alfa: float, confianca: float) -> Resultado:
    """IC de Wald e teste z para uma proporção. `x` é booleano (evento de interesse)."""
    x = pd.Series(x).dropna().astype(bool).to_numpy()
    n = len(x)
    phat = x.mean()
    ep = math.sqrt(phat * (1 - phat) / n)
    z_ic = stats.norm.ppf(1 - (1 - confianca) / 2)
    z = (phat - p0) / math.sqrt(p0 * (1 - p0) / n)  # sob H0 o erro-padrão usa p0
    return Resultado(
        tipo="proporção", n=n, estimativa=phat, erro_padrao=ep,
        ic=(phat - z_ic * ep, phat + z_ic * ep), confianca=confianca,
        valor_h0=p0, alternativa=alternativa, estatistica=z, nome_estatistica="z", gl=None,
        p_valor=_p_valor_normal(z, alternativa), alfa=alfa,
        condicoes={
            "n·p0 ≥ 10": (n * p0, n * p0 >= 10),
            "n·(1−p0) ≥ 10": (n * (1 - p0), n * (1 - p0) >= 10),
            "n·p̂ ≥ 10 e n·(1−p̂) ≥ 10 (IC)": (min(n * phat, n * (1 - phat)), min(n * phat, n * (1 - phat)) >= 10),
        },
    )


def inferir_media(x, mu0: float, alternativa: str, alfa: float, confianca: float) -> Resultado:
    """IC t e teste t de Student para uma média (σ desconhecido)."""
    x = pd.Series(x).dropna().astype(float).to_numpy()
    n = len(x)
    xbar, s = x.mean(), x.std(ddof=1)
    ep = s / math.sqrt(n)
    t_ic = stats.t.ppf(1 - (1 - confianca) / 2, df=n - 1)
    teste = stats.ttest_1samp(x, mu0, alternative=alternativa)
    assim = stats.skew(x)
    return Resultado(
        tipo="média", n=n, estimativa=xbar, erro_padrao=ep,
        ic=(xbar - t_ic * ep, xbar + t_ic * ep), confianca=confianca,
        valor_h0=mu0, alternativa=alternativa, estatistica=float(teste.statistic), nome_estatistica="t",
        gl=n - 1, p_valor=float(teste.pvalue), alfa=alfa,
        condicoes={
            "AAS (observações independentes)": ("por construção", True),
            "n ≥ 30 (TCL)": (n, n >= 30),
            "assimetria da amostra": (assim, abs(assim) < 2 or n >= 100),
        },
    )


def ic_bootstrap_media(x, confianca: float, reps: int = 2000, semente: int = 0) -> tuple[float, float]:
    """IC percentil por bootstrap: checagem de robustez para variáveis assimétricas."""
    x = pd.Series(x).dropna().astype(float).to_numpy()
    rng = np.random.default_rng(semente)
    medias = rng.choice(x, size=(reps, len(x)), replace=True).mean(axis=1)
    a = (1 - confianca) / 2
    return tuple(np.quantile(medias, [a, 1 - a]))


# --------------------------------------------------------------------------- variabilidade amostral
def simular(valores: np.ndarray, n: int, reps: int, tipo: str, valor_h0: float, alternativa: str,
            alfa: float, confianca: float, semente: int = 0) -> pd.DataFrame:
    """Repete a AAS `reps` vezes sobre a população inteira e refaz IC e teste em cada uma.

    `valores` tem uma posição por unidade da população (NaN = fora do domínio da variável),
    então o tamanho efetivo no domínio varia de amostra para amostra, como na amostra real.
    """
    rng = np.random.default_rng(semente)
    N = len(valores)
    linhas = []
    for _ in range(reps):
        x = valores[rng.choice(N, size=n, replace=False)]
        x = x[~np.isnan(x)]
        if tipo == "proporção":
            r = inferir_proporcao(x.astype(bool), valor_h0, alternativa, alfa, confianca)
        else:
            if len(x) < 2:
                continue
            r = inferir_media(x, valor_h0, alternativa, alfa, confianca)
        linhas.append((r.n, r.estimativa, r.ic[0], r.ic[1], r.p_valor, r.rejeita_h0))
    return pd.DataFrame(linhas, columns=["n", "estimativa", "ic_inf", "ic_sup", "p_valor", "rejeita_h0"])


# --------------------------------------------------------------------------- aderência amostra × população
def aderencia_qualitativa(amostra: pd.Series, populacao: pd.Series) -> dict:
    """Qui-quadrado de aderência: as frequências da amostra seguem as proporções da população?

    Categorias com frequência esperada < 5 são agrupadas em "outras" para manter a aproximação válida.
    """
    a, p = amostra.dropna().astype(str), populacao.dropna().astype(str)
    prop = p.value_counts(normalize=True)
    obs = a.value_counts().reindex(prop.index, fill_value=0)
    esp = prop * len(a)
    pequenas = esp < 5
    if pequenas.any() and (~pequenas).sum() >= 2:
        obs = pd.concat([obs[~pequenas], pd.Series({"outras": obs[pequenas].sum()})])
        esp = pd.concat([esp[~pequenas], pd.Series({"outras": esp[pequenas].sum()})])
    r = stats.chisquare(obs.to_numpy(), esp.to_numpy())
    return {"teste": "qui-quadrado", "estatistica": float(r.statistic), "gl": len(obs) - 1,
            "p_valor": float(r.pvalue), "n": len(a), "min_esperada": float(esp.min())}


def aderencia_quantitativa(amostra: pd.Series, populacao: pd.Series) -> dict:
    """Kolmogorov-Smirnov de duas amostras: a distribuição da amostra é a mesma da população?

    Em variáveis discretas (contagens, dias) o KS fica conservador (valor-p maior que o nominal).
    """
    a, p = amostra.dropna().astype(float), populacao.dropna().astype(float)
    r = stats.ks_2samp(a, p)
    return {"teste": "Kolmogorov-Smirnov", "estatistica": float(r.statistic), "gl": None,
            "p_valor": float(r.pvalue), "n": len(a), "min_esperada": None}
