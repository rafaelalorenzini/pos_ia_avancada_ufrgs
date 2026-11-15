import streamlit as st

import graficos as g
from comum import contexto, fmt_num, fmt_rs, hero
from paginas.descritiva import painel

ctx = contexto()
pop = ctx["pop"]

hero("Painel 1 · População", "Análise descritiva da população",
     f"Todas as <b>{fmt_num(len(pop), 0)} licitações</b> de 2025 e 2026 registradas no LicitaCon até "
     f"{ctx['meta']['data_download']}: {fmt_num(pop['CD_ORGAO'].nunique(), 0)} órgãos, 497 municípios e "
     f"{fmt_rs(pop['VL_REF'].sum())} em valor de referência. Estes são os <b>parâmetros</b> que a amostra tenta estimar.",
     g.COR_POP)

painel(pop, None, "População", ctx)
