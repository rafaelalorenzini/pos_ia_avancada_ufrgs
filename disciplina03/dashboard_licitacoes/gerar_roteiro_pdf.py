"""Gera roteiro_video.pdf: roteiro do vídeo de apresentação (item 5 da prova, máximo de 5 minutos).

Uso:  uv run --with reportlab python gerar_roteiro_pdf.py

Os números da fala são os da amostra oficial (semente 20261110) e da população, os mesmos do dashboard e do README.
O tempo de cada bloco é estimado pelo número de palavras da fala, a ~145 palavras por minuto.
"""
from __future__ import annotations

import re
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

SAIDA = Path(__file__).with_name("roteiro_video.pdf")
PALAVRAS_POR_MINUTO = 145
LIMITE_S = 5 * 60

# ----------------------------------------------------------------------------- fontes (acentos, ≤, ≥, ≠, μ)
FONTES = Path("C:/Windows/Fonts")
if (FONTES / "segoeui.ttf").exists():
    for nome, arq in [("Texto", "segoeui.ttf"), ("Texto-B", "segoeuib.ttf"), ("Texto-I", "segoeuii.ttf"),
                      ("Texto-BI", "segoeuiz.ttf")]:
        pdfmetrics.registerFont(TTFont(nome, str(FONTES / arq)))
    pdfmetrics.registerFontFamily("Texto", normal="Texto", bold="Texto-B", italic="Texto-I", boldItalic="Texto-BI")
    F, FB = "Texto", "Texto-B"
else:  # fora do Windows: Helvetica (sem ≤ ≥ ≠ μ)
    F, FB = "Helvetica", "Helvetica-Bold"

# ----------------------------------------------------------------------------- cores (as do dashboard)
AZUL, LARANJA, VERDE, ROXO = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6"
CINZA, TINTA, TINTA_2, MUDO, FUNDO, LINHA = "#898781", "#0b0b0b", "#52514e", "#898781", "#f4f3ef", "#dddbd4"

st = {
    "titulo": ParagraphStyle("titulo", fontName=FB, fontSize=22, leading=27, textColor=TINTA),
    "kicker": ParagraphStyle("kicker", fontName=FB, fontSize=8.5, leading=11, textColor=ROXO),
    "sub": ParagraphStyle("sub", fontName=F, fontSize=10.5, leading=15, textColor=TINTA_2),
    "h2": ParagraphStyle("h2", fontName=FB, fontSize=14, leading=18, textColor=TINTA, spaceBefore=4, spaceAfter=6),
    "h3": ParagraphStyle("h3", fontName=FB, fontSize=11, leading=14, textColor=TINTA, spaceBefore=8, spaceAfter=3),
    "corpo": ParagraphStyle("corpo", fontName=F, fontSize=9.5, leading=13.5, textColor=TINTA_2),
    "item": ParagraphStyle("item", fontName=F, fontSize=9.5, leading=13.5, textColor=TINTA_2, leftIndent=10,
                           bulletIndent=0, spaceAfter=2),
    "tela": ParagraphStyle("tela", fontName=F, fontSize=9, leading=12.5, textColor=TINTA_2),
    "fala": ParagraphStyle("fala", fontName=F, fontSize=11.5, leading=17, textColor=TINTA, alignment=TA_LEFT,
                           spaceAfter=6),
    "nota": ParagraphStyle("nota", fontName=F, fontSize=8.5, leading=11.5, textColor=MUDO),
    "cel": ParagraphStyle("cel", fontName=F, fontSize=8.8, leading=11.8, textColor=TINTA_2),
    "celb": ParagraphStyle("celb", fontName=FB, fontSize=8.8, leading=11.8, textColor=TINTA),
}

H0, H1 = "H<sub>0</sub>", "H<sub>1</sub>"

# ----------------------------------------------------------------------------- roteiro
# (título, cor, na tela, [parágrafos da fala], ênfase)
BLOCOS = [
    ("Abertura", CINZA,
     "<b>Base e amostragem</b>, topo da página. Navegador em tela cheia (F11).",
     ["Olá! Neste trabalho eu uso as compras públicas do Rio Grande do Sul para responder a uma pergunta: "
      "o que uma amostra aleatória de menos de 1% das licitações consegue dizer, com segurança, sobre o total? "
      "E, como eu tenho a população inteira, dá para conferir se a amostra acertou."],
     "Apresente a pergunta, não o sumário. Se quiser, diga seu nome na primeira frase."),

    ("Base de dados e população", AZUL,
     "<b>Base e amostragem · 01</b>: fonte e links, fluxograma da montagem, gráfico de cobertura das variáveis.",
     ["A base é o LicitaCon, do Tribunal de Contas do Estado, publicada em dados abertos. Juntei os conjuntos de "
      "licitações e de contratos de 2025 e 2026, mais a lista de municípios e a população do IBGE.",
      "A população são 305.062 licitações, de 1.180 órgãos, incluindo dispensas e inexigibilidades. "
      "A unidade amostral é a licitação. Duas características pesam em tudo o que vem depois: os valores são "
      "muito assimétricos, e o número de licitantes e o desconto só existem em pregões e concorrências."],
     "Critério 1 (10%): origem, contexto, população e unidade amostral."),

    ("Tamanho da amostra e sorteio", AZUL,
     "<b>Base e amostragem · 02</b>: fórmula com os números, gráfico n × margem de erro, gráfico de uniformidade.",
     ["Dimensionei a amostra pela fórmula de proporção com população finita: 95% de confiança, margem de erro de "
      "2 pontos e p igual a 0,5, o caso mais conservador. Isso dá n igual a 2.383.",
      "Usei 2% em vez dos 5% habituais por causa das hipóteses de média: com 5%, sobrariam só uns 70 pregões e "
      "concorrências e uns 40 descontos. A seleção é uma amostra aleatória simples, sem reposição, com semente fixa, "
      "então qualquer pessoa reproduz a mesma amostra. As sorteadas se espalham de forma uniforme pela lista."],
     "Critério 2 (10%): justifique cada parâmetro, não só leia a fórmula."),

    ("Painéis descritivos: população e amostra", LARANJA,
     "<b>Painel 1</b>: perfil por modalidade, mapa (licitações por 1.000 hab.), curva de concentração. "
     "Depois <b>Painel 2 · 00</b>: diferenças em p.p. e testes de aderência.",
     ["No Painel 1, 56% dos processos são dispensas e outros 18% inexigibilidades: três em cada quatro compras "
      "públicas são contratação direta, sem disputa. A licitação mediana vale cerca de 9.800 reais, mas 1% das "
      "licitações concentra 75% do valor total. E municípios pequenos fazem mais licitações por habitante.",
      "No Painel 2, a amostra reproduz esse retrato: 55% de dispensas, mediana de 9.600 reais. Das 28 categorias, "
      "24 ficam dentro da variação esperada para uma amostra aleatória, e as outras passam do limite por menos de "
      "0,3 ponto. 15 dos 16 testes de aderência não rejeitam a hipótese de mesma distribuição. A única diferença "
      "grande é a média de valor, que cai à metade, porque a amostra raramente pega as poucas licitações gigantes."],
     "Critérios 3 e 4 (20%): diga o que cada número significa; passe o mouse só onde há um número a ler."),

    ("Hipóteses, intervalos e testes", VERDE,
     "<b>Painel 3 · 01</b>: uma aba por hipótese (P1, P2, M1, M2). Mostre H₀ × H₁, o IC e o valor-p em cada aba.",
     ["No Painel 3, toda a inferência usa só a amostra, com 5% de significância.",
      f"Primeira: a maioria das contratações é dispensa? {H0}: p menor ou igual a 50%. A amostra dá 54,6%, com "
      "intervalo de 95% de 52,6 a 56,6%. O intervalo inteiro está acima de 50%, o valor-p é de 3 em um milhão, e "
      f"rejeitamos {H0}: a exceção prevista na lei virou a regra.",
      "Segunda: menos da metade das licitações gera contrato? A amostra dá 41,1%, de 39,1 a 43,1%, e rejeitamos "
      f"{H0}. Ou seja, a base de contratos enxerga só quatro em cada dez licitações.",
      "Terceira: pregões e concorrências têm mais de 3 licitantes em média? Aqui o n cai para 444. A média é 8,7, "
      f"de 7,5 a 9,9, e rejeitamos {H0}. Como a distribuição é assimétrica, conferi com bootstrap, que dá praticamente "
      "o mesmo intervalo. Mas a mediana é 4: a disputa típica é bem menor que a média.",
      "Quarta: o desconto médio é de 20%? Teste bilateral, com 225 casos. A média é 22,3%, de 19,5 a 25,1%. "
      f"O intervalo contém 20, o valor-p é 0,11, e não rejeitamos {H0}. Isso não prova que o desconto é 20%: "
      "só mostra que esta amostra não tem evidência para descartar esse valor."],
     "Critério 5 (20%): em cada hipótese, H₀ → estimativa e IC → valor-p → decisão → o que significa."),

    ("População × amostra e conclusão", VERDE,
     "<b>Painel 3 · 02</b> (resumo: IC × parâmetro) e <b>03</b> (simulação, hipótese M2 selecionada).",
     ["Agora, a comparação com a população. Os quatro intervalos contêm o valor verdadeiro: 55,9% de dispensas, "
      "41,1% com contrato, 8,1 licitantes e 23,4% de desconto. Três decisões estão certas. Em M2, a verdade é 23,4%, "
      f"então {H0} era falsa e cometemos um erro tipo II.",
      "A simulação explica por quê: repetindo o sorteio 500 vezes, o teste de M2 rejeita em só 66% das amostras, "
      "porque 23% está perto demais de 20 para 225 casos. E, nas quatro hipóteses, cerca de 95% dos intervalos "
      "contêm o parâmetro, como a confiança promete.",
      "Conclusão: uma amostra aleatória de 2.383 licitações, bem dimensionada, reproduz a população e acerta as "
      "proporções. Nas médias de domínios pequenos e assimétricos, ela precisa de mais casos para detectar diferenças "
      "pequenas. Agradeço a atenção."],
     "Critério 6 (20%): é aqui que a nota de interpretação se decide. Não corra neste bloco."),
]

CRITERIOS = [
    ("Escolha, descrição e contextualização da base de dados", "10%", "2 · Base de dados e população"),
    ("Dimensionamento e seleção da amostra aleatória simples", "10%", "3 · Tamanho da amostra e sorteio"),
    ("Qualidade e adequação do painel da população", "10%", "4 · Painel 1"),
    ("Qualidade e adequação do painel da amostra", "10%", "4 · Painel 2 (seção 00)"),
    ("Correção dos ICs e testes de hipóteses para médias e proporções", "20%", "5 · P1, P2 (z) e M1, M2 (t)"),
    ("Interpretação dos resultados e comparação população × amostra", "20%", "4 (aderência) e 6 (resumo e simulação)"),
    ("Clareza, objetividade e qualidade da apresentação em vídeo", "20%", "Todos: tempo, fala e gravação"),
]


def palavras(txt: str) -> int:
    return len(re.sub(r"<[^>]+>", "", txt).split())


def mmss(seg: float) -> str:
    seg = int(round(seg))
    return f"{seg // 60}:{seg % 60:02d}"


def tempos():
    t, out = 0.0, []
    for b in BLOCOS:
        dur = sum(palavras(p) for p in b[3]) / PALAVRAS_POR_MINUTO * 60
        out.append((t, t + dur))
        t += dur
    return out


# ----------------------------------------------------------------------------- componentes
def linha_do_tempo(intervalos, largura):
    alt = 30 * mm / 2.2
    d = Drawing(largura, alt + 14)
    escala = largura / LIMITE_S
    for (nome, cor, *_), (a, b) in zip(BLOCOS, intervalos):
        d.add(Rect(a * escala, 12, (b - a) * escala - 1.5, alt, fillColor=colors.HexColor(cor), strokeColor=None))
        d.add(String(a * escala + 3, 12 + alt / 2 - 3, f"{BLOCOS.index((nome, cor, *_)) + 1}", fontName=FB,
                     fontSize=9, fillColor=colors.white))
    fim = intervalos[-1][1]
    d.add(Rect(fim * escala, 12, largura - fim * escala, alt, fillColor=colors.HexColor(FUNDO), strokeColor=None))
    for m in range(6):
        x = min(m * 60 * escala, largura - 0.5)
        d.add(Rect(x, 8, 0.5, 4, fillColor=colors.HexColor(MUDO), strokeColor=None))
        d.add(String(x + (2 if m == 0 else -8 if m == 5 else -4), 0, f"{m}:00", fontName=F, fontSize=7,
                     fillColor=colors.HexColor(MUDO)))
    return d


def caixa_fala(paragrafos, cor, largura):
    t = Table([[[Paragraph(p, st["fala"]) for p in paragrafos]]], colWidths=[largura])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(FUNDO)),
        ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor(cor)),
        ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def cabecalho_bloco(i, nome, cor, a, b, n_pal, largura):
    t = Table([[Paragraph(f"<font color='{cor}'>{i:02d}</font>&nbsp;&nbsp;{nome}", st["h2"]),
                Paragraph(f"<b>{mmss(a)}–{mmss(b)}</b><br/><font color='{MUDO}'>{n_pal} palavras</font>",
                          ParagraphStyle("t", parent=st["tela"], alignment=2))]],
              colWidths=[largura - 32 * mm, 32 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                           ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor(LINHA))]))
    return t


def lista(itens):
    return [Paragraph(i, st["item"], bulletText="•") for i in itens]


def rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont(F, 7.5)
    canvas.setFillColor(colors.HexColor(MUDO))
    canvas.drawString(18 * mm, 10 * mm, "Prova final · Disciplina 03 · Roteiro do vídeo (item 5)")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"{doc.page}")
    canvas.restoreState()


# ----------------------------------------------------------------------------- documento
def gerar():
    intervalos = tempos()
    total = intervalos[-1][1]
    assert total <= LIMITE_S - 10, f"fala estimada em {mmss(total)}: corte texto para caber em 5 min com folga"

    doc = SimpleDocTemplate(str(SAIDA), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=18 * mm, title="Roteiro do vídeo", author="Prova final · Disciplina 03",
                            subject="Item 5: vídeo de apresentação (máximo de 5 minutos)")
    L = doc.width
    e = []

    e += [Paragraph("PROVA FINAL · DISCIPLINA 03 · ITEM 5", st["kicker"]), Spacer(1, 3),
          Paragraph("Roteiro do vídeo", st["titulo"]), Spacer(1, 4),
          Paragraph(f"Amostragem e inferência nas licitações do RS. Fala completa estimada em <b>{mmss(total)}</b> "
                    f"(a {PALAVRAS_POR_MINUTO} palavras por minuto), o que deixa "
                    f"<b>{mmss(LIMITE_S - total)}</b> de folga para trocar de página e respirar. "
                    "Limite da prova: 5:00.", st["sub"]),
          Spacer(1, 10), linha_do_tempo(intervalos, L), Spacer(1, 6)]

    leg = [[Paragraph(f"<font color='{c}'><b>{i}</b></font> {n}", st["nota"]) for i, (n, c, *_) in
            enumerate(BLOCOS, 1)]]
    tl = Table([leg[0][:3], leg[0][3:]], colWidths=[L / 3] * 3)
    tl.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 1),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    e += [tl, Spacer(1, 8)]

    e += [Paragraph("Como usar", st["h3"])]
    e += lista([
        "O texto na caixa cinza é a <b>fala</b>. Leia em voz alta duas ou três vezes antes de gravar; na gravação, "
        "fale com suas palavras, mantendo os números.",
        "<b>Na tela</b> diz onde o dashboard deve estar enquanto você fala. Troque de página <i>antes</i> de começar "
        "a frase seguinte, não no meio.",
        "A prova pede interpretação, não descrição: cada número vem seguido do que ele significa para as compras "
        "públicas. Se o tempo apertar, corte detalhes dos blocos 2 a 4, nunca do bloco 6.",
        "Números da amostra oficial (n = 2.383, semente 20261110). São os mesmos do dashboard e do README.",
    ])

    for i, ((nome, cor, tela, fala, enfase), (a, b)) in enumerate(zip(BLOCOS, intervalos), 1):
        n_pal = sum(palavras(p) for p in fala)
        e += [Spacer(1, 10), KeepTogether([
            cabecalho_bloco(i, nome, cor, a, b, n_pal, L), Spacer(1, 5),
            Paragraph(f"<b>Na tela:</b> {tela}", st["tela"]), Spacer(1, 6),
            caixa_fala(fala, cor, L),
            Spacer(1, 4), Paragraph(f"<b>Atenção:</b> {enfase}", st["nota"])])]

    # critérios
    e += [PageBreak(), Paragraph("Checklist dos critérios de avaliação", st["h2"]),
          Paragraph("Onde cada critério aparece no vídeo. O vídeo vale 20% sozinho, mas também é onde os outros 80% "
                    "são mostrados ao avaliador.", st["corpo"]), Spacer(1, 8)]
    linhas = [[Paragraph("<b>Critério</b>", st["celb"]), Paragraph("<b>Peso</b>", st["celb"]),
               Paragraph("<b>Bloco do roteiro</b>", st["celb"]), Paragraph("<b>OK</b>", st["celb"])]]
    def caixinha():
        d = Drawing(9, 9)
        d.add(Rect(0, 0, 9, 9, fillColor=colors.white, strokeColor=colors.HexColor(TINTA_2), strokeWidth=0.7))
        return d

    linhas += [[Paragraph(c, st["cel"]), Paragraph(p, st["cel"]), Paragraph(o, st["cel"]), caixinha()]
               for c, p, o in CRITERIOS]
    tc = Table(linhas, colWidths=[L * 0.47, L * 0.08, L * 0.37, L * 0.08])
    tc.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor(TINTA_2)),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, colors.HexColor(LINHA)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
    ]))
    e.append(tc)

    # gravação
    e += [PageBreak(), Paragraph("Gravação: tela e voz, sem câmera", st["h2"]),
          Paragraph("<b>Recomendado: OBS Studio</b> (gratuito, obsproject.com). Grava só o que você adicionar como "
                    "fonte: sem fonte de câmera, só aparecem a tela e a sua voz.", st["corpo"]), Spacer(1, 3)]
    e += lista([
        "Fontes: <b>+ › Captura de janela</b> (o navegador com o dashboard) ou <b>Captura de tela</b> (o monitor "
        "inteiro). Não adicione Dispositivo de captura de vídeo.",
        "Áudio (Configurações › Áudio): <b>Microfone/Áudio auxiliar</b> = seu microfone; <b>Áudio da área de "
        "trabalho</b> = Desativado, para não gravar sons de notificação.",
        "Vídeo: resolução base e de saída <b>1920×1080</b>, 30 FPS. Saída: formato <b>MP4</b> (ou MKV e depois "
        "Arquivo › Remux para MP4).",
        "No mixer, fale normalmente e confira se o nível do microfone fica no amarelo, sem chegar ao vermelho. "
        "Em Filtros do microfone, <b>Supressão de ruído</b> ajuda em ambiente barulhento.",
        "Faça um teste de 20 segundos e ouça antes de gravar o vídeo inteiro.",
    ])
    e += [Spacer(1, 6),
          Paragraph("<b>Alternativa rápida: Ferramenta de Captura do Windows 11</b> (Win + Shift + R). Selecione a "
                    "área, ligue o microfone no botão de áudio e grave; sai em MP4. Não tem pausa nem configuração de "
                    "qualidade, então funciona melhor gravando de uma vez.", st["corpo"]), Spacer(1, 10)]

    e += [Paragraph("Antes de gravar", st["h3"])]
    e += lista([
        "Rode o app e abra cada página uma vez, para os gráficos já estarem em cache e não aparecer “carregando”.",
        "Navegador em tela cheia (F11), zoom de 90%, sem favoritos nem outras abas. Ative o Não incomodar do Windows.",
        "Barra lateral com <b>Sortear outra amostra</b> desligado (amostra oficial).",
        "Deixe o Painel 3 com α = 5% e a simulação já em M2, para o bloco 6.",
        "Se errar, pause dois segundos e repita a frase: dá para cortar depois (Clipchamp, que vem no Windows, "
        "corta e junta trechos).",
    ])
    e += [Paragraph("Entrega", st["h3"])]
    e += lista([
        "YouTube: envie com visibilidade <b>Não listado</b> (ou Público). Não listado abre para quem tem o link, "
        "sem pedir autorização; <b>Privado</b> não serve.",
        "Confira a duração (no máximo 5:00) e teste os três links (painéis, vídeo, base do TCE-RS) numa janela "
        "anônima antes de entregar.",
    ])

    doc.build(e, onFirstPage=rodape, onLaterPages=rodape)
    for (nome, *_), (a, b) in zip(BLOCOS, intervalos):
        print(f"{mmss(a)}–{mmss(b)}  {nome}")
    print(f"total {mmss(total)} → {SAIDA.name}")


if __name__ == "__main__":
    gerar()
