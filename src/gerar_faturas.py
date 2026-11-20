"""
Gerador de faturas fictícias em PDF.

Cria faturas de fornecedores fictícios em dois layouts diferentes,
simulando o cenário real em que cada fornecedor emite documentos
com formatação própria. Algumas faturas são geradas propositalmente
com inconsistências (total divergente da soma dos itens) para que o
pipeline de validação tenha o que detectar.

Uso:
    python src/gerar_faturas.py
"""

import random
from datetime import date, timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------

PASTA_SAIDA = Path(__file__).resolve().parent.parent / "dados" / "pdfs"
QTD_FATURAS = 60
QTD_COM_ERRO = 4  # faturas geradas com total propositalmente divergente
SEMENTE = 42  # para resultados reproduzíveis

# Fornecedores fictícios: (razão social, cidade/UF, layout)
FORNECEDORES = [
    ("Alfa Suprimentos Industriais Ltda", "Contagem/MG", "A"),
    ("Beta Materiais e Equipamentos SA", "Betim/MG", "A"),
    ("Gama Distribuidora de Pecas Ltda", "Belo Horizonte/MG", "B"),
    ("Delta Comercio de EPIs Eireli", "Sete Lagoas/MG", "B"),
    ("Omega Ferramentas e Abrasivos Ltda", "Juiz de Fora/MG", "A"),
    ("Sigma Eletrica e Automacao Ltda", "Uberlandia/MG", "B"),
]

CATALOGO_ITENS = [
    ("MAT-1001", "Luva de protecao nitrilica", "PAR", 8.50),
    ("MAT-1002", "Oculos de seguranca incolor", "UN", 12.90),
    ("MAT-1003", "Capacete de seguranca classe B", "UN", 34.00),
    ("MAT-1004", "Protetor auricular tipo plug", "UN", 2.75),
    ("MAT-2001", "Parafuso sextavado M8 x 40mm", "CT", 45.00),
    ("MAT-2002", "Arruela lisa M8 aco zincado", "CT", 18.30),
    ("MAT-2003", "Porca sextavada M8", "CT", 22.10),
    ("MAT-3001", "Disco de corte 7 pol", "UN", 9.80),
    ("MAT-3002", "Disco de desbaste 7 pol", "UN", 11.40),
    ("MAT-3003", "Eletrodo revestido E6013 3,25mm", "KG", 28.90),
    ("MAT-4001", "Oleo lubrificante ISO VG 68", "LT", 19.60),
    ("MAT-4002", "Graxa multiuso a base de litio", "KG", 31.20),
    ("MAT-5001", "Cabo flexivel 2,5mm2 750V", "MT", 3.45),
    ("MAT-5002", "Disjuntor monopolar 20A", "UN", 24.70),
    ("MAT-5003", "Contator tripolar 25A", "UN", 118.00),
    ("MAT-6001", "Fita isolante 19mm x 20m", "UN", 7.25),
    ("MAT-6002", "Abracadeira de nylon 200mm", "CT", 15.80),
    ("MAT-7001", "Tinta esmalte sintetico azul 3,6L", "GL", 89.90),
]

CONDICOES_PAGAMENTO = ["28 DDL", "30 DDL", "45 DDL", "60 DDL", "A VISTA"]


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def gerar_cnpj() -> str:
    """Gera um CNPJ fictício com dígitos verificadores válidos."""
    base = [random.randint(0, 9) for _ in range(8)] + [0, 0, 0, 1]

    def dv(nums: list[int]) -> int:
        pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2][-len(nums):]
        resto = sum(n * p for n, p in zip(nums, pesos)) % 11
        return 0 if resto < 2 else 11 - resto

    d1 = dv(base)
    d2 = dv(base + [d1])
    nums = base + [d1, d2]
    s = "".join(map(str, nums))
    return f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}"


def formatar_moeda(valor: float) -> str:
    """Formata um número no padrão monetário brasileiro (1.234,56)."""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_itens() -> list[dict]:
    """Sorteia de 3 a 8 itens do catálogo com quantidades variadas."""
    itens = []
    for codigo, descricao, unidade, preco_base in random.sample(
        CATALOGO_ITENS, k=random.randint(3, 8)
    ):
        quantidade = random.randint(1, 50)
        # variação de até +/- 10% sobre o preço de tabela
        preco = round(preco_base * random.uniform(0.9, 1.1), 2)
        itens.append(
            {
                "codigo": codigo,
                "descricao": descricao,
                "unidade": unidade,
                "quantidade": quantidade,
                "valor_unitario": preco,
                "valor_total": round(quantidade * preco, 2),
            }
        )
    return itens


# ---------------------------------------------------------------------------
# Layouts de PDF
# ---------------------------------------------------------------------------

def _estilos():
    estilos = getSampleStyleSheet()
    estilos.add(ParagraphStyle("TituloFatura", fontSize=16, leading=20, spaceAfter=4))
    estilos.add(ParagraphStyle("Campo", fontSize=9, leading=12))
    estilos.add(ParagraphStyle("CampoNegrito", fontSize=9, leading=12, fontName="Helvetica-Bold"))
    return estilos


def montar_layout_a(caminho: Path, fatura: dict) -> None:
    """Layout A: cabeçalho em tabela de campos + tabela de itens com grade."""
    estilos = _estilos()
    doc = SimpleDocTemplate(str(caminho), pagesize=A4,
                            topMargin=18 * mm, bottomMargin=18 * mm)
    elementos = [
        Paragraph("FATURA DE FORNECIMENTO", estilos["TituloFatura"]),
        Paragraph(fatura["fornecedor"], estilos["CampoNegrito"]),
        Paragraph(f"CNPJ: {fatura['cnpj']} - {fatura['cidade']}", estilos["Campo"]),
        Spacer(1, 6 * mm),
    ]

    cabecalho = Table(
        [
            ["Numero da fatura:", fatura["numero"],
             "Data de emissao:", fatura["data_emissao"]],
            ["Condicao de pagamento:", fatura["condicao_pagamento"],
             "Data de vencimento:", fatura["data_vencimento"]],
        ],
        colWidths=[45 * mm, 45 * mm, 42 * mm, 38 * mm],
    )
    cabecalho.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elementos += [cabecalho, Spacer(1, 6 * mm)]

    linhas = [["Codigo", "Descricao", "Un", "Qtd", "Vlr Unit (R$)", "Vlr Total (R$)"]]
    for item in fatura["itens"]:
        linhas.append([
            item["codigo"], item["descricao"], item["unidade"],
            str(item["quantidade"]),
            formatar_moeda(item["valor_unitario"]),
            formatar_moeda(item["valor_total"]),
        ])
    linhas.append(["", "", "", "", "TOTAL",
                   formatar_moeda(fatura["total_declarado"])])

    tabela = Table(linhas, colWidths=[22 * mm, 68 * mm, 12 * mm, 14 * mm, 27 * mm, 27 * mm])
    tabela.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (-2, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -2), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDDDDD")),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elementos.append(tabela)
    doc.build(elementos)


def montar_layout_b(caminho: Path, fatura: dict) -> None:
    """Layout B: campos rotulados em linhas de texto + tabela de itens sem grade."""
    estilos = _estilos()
    doc = SimpleDocTemplate(str(caminho), pagesize=A4,
                            topMargin=18 * mm, bottomMargin=18 * mm)
    elementos = [
        Paragraph(fatura["fornecedor"].upper(), estilos["TituloFatura"]),
        Paragraph(f"CNPJ {fatura['cnpj']} | {fatura['cidade']}", estilos["Campo"]),
        Spacer(1, 4 * mm),
        Paragraph("DOCUMENTO DE COBRANCA", estilos["CampoNegrito"]),
        Spacer(1, 2 * mm),
        Paragraph(f"Fatura No: {fatura['numero']}", estilos["Campo"]),
        Paragraph(f"Emissao: {fatura['data_emissao']}", estilos["Campo"]),
        Paragraph(f"Vencimento: {fatura['data_vencimento']}", estilos["Campo"]),
        Paragraph(f"Pagamento: {fatura['condicao_pagamento']}", estilos["Campo"]),
        Spacer(1, 6 * mm),
    ]

    linhas = [["Item", "Un", "Qtd", "Unitario", "Total"]]
    for item in fatura["itens"]:
        linhas.append([
            f"{item['codigo']} - {item['descricao']}",
            item["unidade"],
            str(item["quantidade"]),
            formatar_moeda(item["valor_unitario"]),
            formatar_moeda(item["valor_total"]),
        ])

    tabela = Table(linhas, colWidths=[90 * mm, 12 * mm, 14 * mm, 27 * mm, 27 * mm])
    tabela.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.black),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elementos += [
        tabela,
        Spacer(1, 4 * mm),
        Paragraph(
            f"VALOR TOTAL DO DOCUMENTO: R$ {formatar_moeda(fatura['total_declarado'])}",
            estilos["CampoNegrito"],
        ),
    ]
    doc.build(elementos)


# ---------------------------------------------------------------------------
# Geração das faturas
# ---------------------------------------------------------------------------

def gerar_faturas() -> None:
    random.seed(SEMENTE)
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

    cnpjs = {nome: gerar_cnpj() for nome, _, _ in FORNECEDORES}
    indices_com_erro = set(random.sample(range(QTD_FATURAS), k=QTD_COM_ERRO))

    for i in range(QTD_FATURAS):
        fornecedor, cidade, layout = random.choice(FORNECEDORES)
        itens = gerar_itens()
        total_real = round(sum(item["valor_total"] for item in itens), 2)

        # Algumas faturas saem com total divergente de propósito,
        # simulando erro de digitação do fornecedor.
        if i in indices_com_erro:
            total_declarado = round(total_real * random.uniform(1.02, 1.15), 2)
        else:
            total_declarado = total_real

        emissao = date(2026, 1, 1) + timedelta(days=random.randint(0, 300))
        prazo = {"A VISTA": 0, "28 DDL": 28, "30 DDL": 30,
                 "45 DDL": 45, "60 DDL": 60}
        condicao = random.choice(CONDICOES_PAGAMENTO)
        vencimento = emissao + timedelta(days=prazo[condicao])

        fatura = {
            "numero": f"FAT-{2026}{i + 1:04d}",
            "fornecedor": fornecedor,
            "cnpj": cnpjs[fornecedor],
            "cidade": cidade,
            "data_emissao": emissao.strftime("%d/%m/%Y"),
            "data_vencimento": vencimento.strftime("%d/%m/%Y"),
            "condicao_pagamento": condicao,
            "itens": itens,
            "total_declarado": total_declarado,
        }

        caminho = PASTA_SAIDA / f"{fatura['numero']}.pdf"
        if layout == "A":
            montar_layout_a(caminho, fatura)
        else:
            montar_layout_b(caminho, fatura)

    print(f"{QTD_FATURAS} faturas geradas em {PASTA_SAIDA}")
    print(f"(sendo {QTD_COM_ERRO} com total propositalmente divergente)")


if __name__ == "__main__":
    gerar_faturas()
