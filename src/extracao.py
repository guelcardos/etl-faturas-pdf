"""
Funções de extração de dados das faturas em PDF.

Cada fornecedor emite a fatura em um layout próprio. Este módulo
detecta o layout do documento e aplica a estratégia adequada:

- Layout A ("FATURA DE FORNECIMENTO"): campos e itens em tabelas
  com grade -> extração via `extract_tables` do pdfplumber.
- Layout B ("DOCUMENTO DE COBRANCA"): campos rotulados em linhas de
  texto e tabela sem grade -> extração via texto + expressões regulares.
"""

import re
from pathlib import Path

import pdfplumber


def converter_moeda(texto: str) -> float:
    """Converte '1.234,56' (padrão brasileiro) para float 1234.56."""
    return float(texto.strip().replace(".", "").replace(",", "."))


def detectar_layout(texto: str) -> str:
    """Identifica o layout da fatura pelo título do documento."""
    if "FATURA DE FORNECIMENTO" in texto:
        return "A"
    if "DOCUMENTO DE COBRANCA" in texto:
        return "B"
    raise ValueError("Layout de fatura não reconhecido")


# ---------------------------------------------------------------------------
# Layout A — tabelas com grade
# ---------------------------------------------------------------------------

def extrair_layout_a(pagina, texto: str) -> dict:
    """Extrai os dados de uma fatura no layout A.

    O cabeçalho não possui grade, então é lido do texto com expressões
    regulares; a tabela de itens tem grade e é lida com `extract_tables`.
    """
    linhas_texto = texto.splitlines()

    fornecedor = linhas_texto[1].strip()
    cnpj = re.search(r"CNPJ:\s*([\d./-]+)", texto).group(1)

    numero = re.search(r"Numero da fatura:\s*(\S+)", texto).group(1)
    emissao = re.search(r"Data de emissao:\s*([\d/]+)", texto).group(1)
    vencimento = re.search(r"Data de vencimento:\s*([\d/]+)", texto).group(1)
    condicao = re.search(
        r"Condicao de pagamento:\s*(.+?)\s+Data de vencimento", texto
    ).group(1).strip()

    # localiza a tabela de itens (a única com grade no documento)
    tabela_itens = None
    for tabela in pagina.extract_tables():
        if tabela and (tabela[0][0] or "").strip() == "Codigo":
            tabela_itens = tabela
            break
    if tabela_itens is None:
        raise ValueError("Tabela de itens não encontrada no layout A")

    itens = []
    for linha in tabela_itens[1:]:
        if not (linha[0] or "").strip():  # linha do TOTAL ou vazia
            continue
        itens.append(
            {
                "codigo": linha[0].strip(),
                "descricao": linha[1].strip(),
                "unidade": linha[2].strip(),
                "quantidade": int(linha[3]),
                "valor_unitario": converter_moeda(linha[4]),
                "valor_total": converter_moeda(linha[5]),
            }
        )

    total = converter_moeda(re.search(r"TOTAL\s+([\d.,]+)", texto).group(1))

    return {
        "numero": numero,
        "fornecedor": fornecedor,
        "cnpj": cnpj,
        "data_emissao": emissao,
        "data_vencimento": vencimento,
        "condicao_pagamento": condicao,
        "itens": itens,
        "total_declarado": total,
    }


# ---------------------------------------------------------------------------
# Layout B — texto + expressões regulares
# ---------------------------------------------------------------------------

PADRAO_ITEM_B = re.compile(
    r"^(?P<codigo>MAT-\d+) - (?P<descricao>.+?) "
    r"(?P<unidade>[A-Z]{2,3}) (?P<quantidade>\d+) "
    r"(?P<valor_unitario>[\d.,]+) (?P<valor_total>[\d.,]+)$"
)


def extrair_layout_b(texto: str) -> dict:
    """Extrai os dados de uma fatura no layout B (texto corrido)."""
    linhas = texto.splitlines()

    fornecedor = linhas[0].strip().title()
    cnpj = re.search(r"CNPJ\s+([\d./-]+)", texto).group(1)

    def campo(rotulo: str) -> str:
        return re.search(rf"{rotulo}:\s*(.+)", texto).group(1).strip()

    itens = []
    for linha in linhas:
        m = PADRAO_ITEM_B.match(linha.strip())
        if m:
            itens.append(
                {
                    "codigo": m["codigo"],
                    "descricao": m["descricao"],
                    "unidade": m["unidade"],
                    "quantidade": int(m["quantidade"]),
                    "valor_unitario": converter_moeda(m["valor_unitario"]),
                    "valor_total": converter_moeda(m["valor_total"]),
                }
            )

    total = converter_moeda(
        re.search(r"VALOR TOTAL DO DOCUMENTO:\s*R\$\s*([\d.,]+)", texto).group(1)
    )

    return {
        "numero": campo("Fatura No"),
        "fornecedor": fornecedor,
        "cnpj": cnpj,
        "data_emissao": campo("Emissao"),
        "data_vencimento": campo("Vencimento"),
        "condicao_pagamento": campo("Pagamento"),
        "itens": itens,
        "total_declarado": total,
    }


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

def extrair_fatura(caminho: Path) -> dict:
    """Abre um PDF de fatura, detecta o layout e extrai os dados."""
    with pdfplumber.open(caminho) as pdf:
        pagina = pdf.pages[0]
        texto = pagina.extract_text()
        layout = detectar_layout(texto)
        if layout == "A":
            dados = extrair_layout_a(pagina, texto)
        else:
            dados = extrair_layout_b(texto)

    dados["arquivo"] = caminho.name
    dados["layout"] = layout
    return dados
