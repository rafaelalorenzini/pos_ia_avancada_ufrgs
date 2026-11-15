"""Monta a população (licitações 2025-2026 + contratos) e sorteia a amostra oficial — versão 2.

Uso:  uv run python preparar_dados.py

Monta a população (uma linha por licitação), as variáveis descritivas (objeto, natureza, datas, prazos, município),
dimensiona e sorteia a amostra aleatória simples.

Saídas em data/:
  populacao.parquet   uma linha por licitação (a unidade amostral)
  amostra.parquet     a AAS oficial usada no trabalho
  municipios.parquet  municípios do RS (IBGE) com população 2022, para o mapa
  metadados.json      parâmetros do dimensionamento, semente, data dos dados e checagens
"""
from __future__ import annotations

import json
import re
import unicodedata
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from estatistica import sortear_aas, tamanho_amostra

AQUI = Path(__file__).parent
RAW = AQUI.parent / "data" / "raw"      # mesmos zips usados pelo notebook
OUT = AQUI / "data"
IBGE = OUT / "ibge"
ANOS = [2025, 2026]
URL = "https://dados.tce.rs.gov.br/dados/licitacon/{conjunto}/ano/{ano}.csv.zip"
URL_IBGE = {
    "municipios_rs.json": "https://servicodados.ibge.gov.br/api/v1/localidades/estados/43/municipios",
    "malha_rs.geojson": "https://servicodados.ibge.gov.br/api/v3/malhas/estados/43"
                        "?formato=application/vnd.geo%2Bjson&intrarregiao=municipio&qualidade=minima",
    "populacao_2022.json": "https://apisidra.ibge.gov.br/values/t/4709/n6/in%20n3%2043/v/93/p/2022",
}
CHAVE_LIC = ["CD_ORGAO", "NR_LICITACAO", "ANO_LICITACAO", "CD_TIPO_MODALIDADE"]
CHAVE_CON = CHAVE_LIC + ["NR_CONTRATO", "ANO_CONTRATO", "TP_INSTRUMENTO"]

# Parâmetros do dimensionamento
CONFIANCA = 0.95
MARGEM = 0.02
P_PLANEJAMENTO = 0.5
SEMENTE = 20261110

TETO = 20e9  # acima disso o valor é tratado como erro de cadastro (maior PPP real do período ≈ R$ 10 bi)
MAX_DIAS = 730  # prazos acima de 2 anos (ou negativos) são tratados como erro de data

GRUPO_MODALIDADE = {
    "PRD": "Dispensa", "PDE": "Dispensa",              # art. 75 (PDE = dispensa eletrônica)
    "PRI": "Inexigibilidade",                          # art. 74
    "PCE": "Pregão", "PCP": "Pregão",                  # art. 28, I
    "CCE": "Concorrência", "CCP": "Concorrência",      # art. 28, II
}
COMPETITIVAS = {"PCE", "PCP", "CCE", "CCP"}

# TP_OBJETO: rótulos conferidos lendo as descrições (DS_OBJETO) de cada código
GRUPO_OBJETO = {
    "COM": "Compras",
    "OUS": "Outros serviços",
    "CSE": "Compras e serviços",
    "OSE": "Obras e serv. de engenharia",
}  # LOC, SAU, INF, ALB, CON, PER, COL, PRI (≈ 3%) → "Outros"
NATUREZA = {"N": "Normal", "R": "Registro de preços", "O": "Outros"}


def baixar(conjunto: str, ano: int) -> Path:
    destino = RAW / f"{conjunto}_{ano}.zip"
    if not destino.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        print(f"baixando {conjunto} {ano} ...")
        urllib.request.urlretrieve(URL.format(conjunto=conjunto, ano=ano), destino)
    return destino


def baixar_ibge() -> None:
    IBGE.mkdir(parents=True, exist_ok=True)
    for nome, url in URL_IBGE.items():
        if not (IBGE / nome).exists():
            print(f"baixando IBGE {nome} ...")
            urllib.request.urlretrieve(url, IBGE / nome)


def ler(conjunto: str, arquivo: str, **kw) -> pd.DataFrame:
    partes = []
    for ano in ANOS:
        with zipfile.ZipFile(baixar(conjunto, ano)) as z, z.open(arquivo) as fh:
            partes.append(pd.read_csv(fh, dtype=str, encoding="utf-8-sig", low_memory=False, **kw))
    return pd.concat(partes, ignore_index=True)


def num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def data(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce", format="%Y-%m-%d")


def normalizar(nome: str) -> str:
    """Caixa alta, sem acento e sem pontuação: 'Sant'Ana do Livramento' → 'SANTANA DO LIVRAMENTO'."""
    s = unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Z0-9 ]", "", s.upper().replace("-", " "))
    return re.sub(r"\s+", " ", s).strip()


def tipo_orgao(nome: pd.Series) -> pd.Series:
    prefixo = nome.str.extract(r"^(\w+)")[0]
    return prefixo.map({"PM": "Prefeitura", "CM": "Câmara de Vereadores"}).fillna("Outros (Estado, autarquias, consórcios…)")


def municipios_ibge() -> pd.DataFrame:
    baixar_ibge()
    lista = json.loads((IBGE / "municipios_rs.json").read_text(encoding="utf-8"))
    mun = pd.DataFrame({
        "COD_IBGE": [str(m["id"]) for m in lista],
        "MUNICIPIO": [m["nome"] for m in lista],
        "MESORREGIAO": [m["microrregiao"]["mesorregiao"]["nome"] for m in lista],
    })
    sidra = json.loads((IBGE / "populacao_2022.json").read_text(encoding="utf-8"))[1:]
    popm = pd.DataFrame({"COD_IBGE": [r["D1C"] for r in sidra], "POP_2022": [num(pd.Series([r["V"]]))[0] for r in sidra]})
    mun = mun.merge(popm, on="COD_IBGE", how="left")
    mun["CHAVE"] = mun["MUNICIPIO"].map(normalizar)
    return mun


def casar_municipio(nm_orgao: pd.Series, tipo: pd.Series, mun: pd.DataFrame) -> pd.DataFrame:
    """Prefeituras e câmaras ('PM DE X', 'CM DE X') → código IBGE do município X."""
    nome = nm_orgao.str.replace(r"^(PM|CM)\s+(DE|DA|DO|DOS|DAS)?\s*", "", regex=True)
    chave = nome.map(normalizar).where(tipo.isin(["Prefeitura", "Câmara de Vereadores"]))
    mapa = mun.set_index("CHAVE")
    return pd.DataFrame({
        "COD_IBGE": chave.map(mapa["COD_IBGE"]),
        "MUNICIPIO": chave.map(mapa["MUNICIPIO"]),
        "MESORREGIAO": chave.map(mapa["MESORREGIAO"]),
        "_chave": chave,
    })


def main() -> None:
    print("lendo licitações ...")
    lic = ler("licitacao", "licitacao.csv",
              usecols=CHAVE_LIC + ["NM_ORGAO", "VL_LICITACAO", "VL_HOMOLOGADO", "DT_ABERTURA", "DT_HOMOLOGACAO",
                                   "TP_OBJETO", "TP_NATUREZA", "BL_PERMITE_CONSORCIO"])
    for c in ["VL_LICITACAO", "VL_HOMOLOGADO"]:
        lic[c] = num(lic[c])

    # ---- valor de referência e valores suspeitos
    vl_ref = lic["VL_HOMOLOGADO"].where(lic["VL_HOMOLOGADO"] > 0, lic["VL_LICITACAO"])
    ambos = (lic["VL_LICITACAO"] > 0) & (lic["VL_HOMOLOGADO"] > 0)
    razao = lic["VL_HOMOLOGADO"] / lic["VL_LICITACAO"]
    suspeito = (lic[["VL_LICITACAO", "VL_HOMOLOGADO"]].max(axis=1) > TETO) | (ambos & ((razao > 100) | (razao < 0.01)))

    pop = lic[CHAVE_LIC + ["NM_ORGAO"]].copy()
    pop["ANO"] = lic["ANO_LICITACAO"].astype(int)
    pop["MODALIDADE"] = lic["CD_TIPO_MODALIDADE"]
    pop["MODALIDADE_GRUPO"] = lic["CD_TIPO_MODALIDADE"].map(GRUPO_MODALIDADE).fillna("Outras")
    pop["TIPO_ORGAO"] = tipo_orgao(lic["NM_ORGAO"])
    pop["VALOR_SUSPEITO"] = suspeito
    pop["VL_REF"] = vl_ref.where((vl_ref > 0) & ~suspeito)
    pop["LOG10_VL_REF"] = np.log10(pop["VL_REF"])
    pop["DISPENSA"] = pop["MODALIDADE_GRUPO"].eq("Dispensa")
    pop["COMPETITIVA"] = lic["CD_TIPO_MODALIDADE"].isin(COMPETITIVAS)

    ok_desc = pop["COMPETITIVA"] & ambos & ~suspeito & (razao <= 2)
    pop["DESCONTO_PCT"] = ((1 - razao) * 100).where(ok_desc)

    # ---- variáveis descritivas
    pop["OBJETO"] = lic["TP_OBJETO"].map(GRUPO_OBJETO).fillna("Outros")
    pop["NATUREZA"] = lic["TP_NATUREZA"].map(NATUREZA).fillna("Outros")
    pop["REGISTRO_PRECOS"] = lic["TP_NATUREZA"].eq("R")
    pop["PERMITE_CONSORCIO"] = lic["BL_PERMITE_CONSORCIO"].map({"S": True, "N": False}).astype("boolean")
    dt_ab, dt_ho = data(lic["DT_ABERTURA"]), data(lic["DT_HOMOLOGACAO"])
    dt_ab = dt_ab.where(dt_ab.between("2024-01-01", "2027-12-31"))
    pop["DT_ABERTURA"] = dt_ab
    pop["MES_ABERTURA"] = dt_ab.dt.to_period("M").dt.to_timestamp()
    dias = (dt_ho - dt_ab).dt.days
    pop["DIAS_ATE_HOMOLOGACAO"] = dias.where(pop["COMPETITIVA"] & dias.between(0, MAX_DIAS)).astype(float)

    # ---- número de licitantes
    print("lendo licitantes ...")
    lt = ler("licitacao", "licitante.csv", usecols=[0, 1, 2, 3, 4, 5])
    lt.columns = CHAVE_LIC + ["TP_DOC", "NR_DOC"]
    n_lic = lt.drop_duplicates().groupby(CHAVE_LIC).size().rename("N_LICITANTES").reset_index()
    pop = pop.merge(n_lic, on=CHAVE_LIC, how="left")
    pop["N_LICITANTES"] = pop["N_LICITANTES"].where(pop["COMPETITIVA"])

    # ---- contratos, aditivos e prazo de vigência
    print("lendo contratos ...")
    con = ler("contrato", "contrato.csv", usecols=CHAVE_CON + ["VL_CONTRATO", "DT_INICIO_VIGENCIA", "DT_FINAL_VIGENCIA"])
    con["VL_CONTRATO"] = num(con["VL_CONTRATO"]).where(lambda s: s <= TETO)
    vig = (data(con["DT_FINAL_VIGENCIA"]) - data(con["DT_INICIO_VIGENCIA"])).dt.days
    con["VIGENCIA_DIAS"] = vig.where(vig.between(1, 3650))  # até 10 anos (concessões longas ficam de fora)
    alt = ler("contrato", "alteracao.csv", usecols=CHAVE_CON)
    con["TEM_ADITIVO"] = con.set_index(CHAVE_CON).index.isin(alt.set_index(CHAVE_CON).index)
    agg = (con.groupby(CHAVE_LIC)
              .agg(N_CONTRATOS=("NR_CONTRATO", "size"), VL_CONTRATADO=("VL_CONTRATO", "sum"),
                   TEM_ADITIVO=("TEM_ADITIVO", "any"), PRAZO_VIGENCIA_DIAS=("VIGENCIA_DIAS", "median"))
              .reset_index())
    pop = pop.merge(agg, on=CHAVE_LIC, how="left")
    pop["TEM_CONTRATO"] = pop["N_CONTRATOS"].notna()
    pop["N_CONTRATOS"] = pop["N_CONTRATOS"].fillna(0).astype(int)
    pop["VL_CONTRATADO"] = pop["VL_CONTRATADO"].where(pop["TEM_CONTRATO"] & (pop["VL_CONTRATADO"] > 0))
    pop["TEM_ADITIVO"] = pop["TEM_ADITIVO"].astype("boolean").where(pop["TEM_CONTRATO"])

    # ---- município (prefeituras e câmaras) via IBGE
    mun = municipios_ibge()
    cas = casar_municipio(pop["NM_ORGAO"], pop["TIPO_ORGAO"], mun)
    pop[["COD_IBGE", "MUNICIPIO", "MESORREGIAO"]] = cas[["COD_IBGE", "MUNICIPIO", "MESORREGIAO"]]
    orgaos_munic = cas.assign(CD_ORGAO=pop["CD_ORGAO"], NM_ORGAO=pop["NM_ORGAO"]).dropna(subset=["_chave"]) \
                      .drop_duplicates("CD_ORGAO")
    taxa_casamento = orgaos_munic["COD_IBGE"].notna().mean()
    nao_casados = sorted(orgaos_munic.loc[orgaos_munic["COD_IBGE"].isna(), "NM_ORGAO"].tolist())

    # ---- ordem fixa (mesma chave → mesma amostra)
    pop = pop.sort_values(CHAVE_LIC, kind="mergesort").reset_index(drop=True)
    pop.insert(0, "ID", np.arange(1, len(pop) + 1))

    # ---- dimensionamento e AAS
    N = len(pop)
    dim = tamanho_amostra(N, CONFIANCA, MARGEM, P_PLANEJAMENTO)
    amostra = sortear_aas(pop, dim["n"], SEMENTE)

    OUT.mkdir(exist_ok=True)
    pop.to_parquet(OUT / "populacao.parquet", index=False)
    amostra.to_parquet(OUT / "amostra.parquet", index=False)
    mun.drop(columns="CHAVE").to_parquet(OUT / "municipios.parquet", index=False)
    dt_dados = datetime.fromtimestamp(baixar("licitacao", 2026).stat().st_mtime).strftime("%d/%m/%Y")
    meta = {
        "N": N, "n": dim["n"], "n0": dim["n0"], "n_exato": dim["n_exato"], "z": dim["z"],
        "confianca": CONFIANCA, "margem": MARGEM, "p_planejamento": P_PLANEJAMENTO,
        "semente": SEMENTE, "data_download": dt_dados,
        "n_registros_contratos": len(con), "n_registros_alteracoes": len(alt),
        "n_registros_licitantes": len(lt),
        "taxa_casamento_municipios": taxa_casamento, "orgaos_municipais_nao_casados": nao_casados,
        "ultimo_mes_abertura": str(pop["MES_ABERTURA"].max().date()),
    }
    (OUT / "metadados.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"população: {N:,} licitações × {pop.shape[1]} colunas")
    print(f"amostra:   n = {dim['n']:,} (n0 = {dim['n0']:.1f}; fração {dim['fracao']:.2%}); semente {SEMENTE}")
    print(f"municípios: {taxa_casamento:.1%} dos órgãos municipais casados com o IBGE; sem casamento: {nao_casados[:10]}")
    resumo = pd.DataFrame({
        "pop": [pop["DISPENSA"].mean(), pop["TEM_CONTRATO"].mean(), pop["N_LICITANTES"].mean(), pop["DESCONTO_PCT"].mean()],
        "amostra": [amostra["DISPENSA"].mean(), amostra["TEM_CONTRATO"].mean(), amostra["N_LICITANTES"].mean(),
                    amostra["DESCONTO_PCT"].mean()],
    }, index=["% dispensa", "% com contrato", "média licitantes", "média desconto %"])
    print(resumo)


if __name__ == "__main__":
    main()
