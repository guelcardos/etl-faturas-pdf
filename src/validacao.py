"""
Regras de validação aplicadas às faturas extraídas.

Cada regra devolve uma lista de inconsistências encontradas, no formato:
    {"fatura": ..., "regra": ..., "detalhe": ...}
"""

from datetime import datetime

TOLERANCIA = 0.01  # tolerância para comparações monetárias (centavos)


def validar_cnpj(cnpj: str) -> bool:
    """Confere os dígitos verificadores de um CNPJ."""
    nums = [int(c) for c in cnpj if c.isdigit()]
    if len(nums) != 14:
        return False

    def dv(parcial: list[int]) -> int:
        pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2][-len(parcial):]
        resto = sum(n * p for n, p in zip(parcial, pesos)) % 11
        return 0 if resto < 2 else 11 - resto

    return nums[12] == dv(nums[:12]) and nums[13] == dv(nums[:13])


def validar_fatura(fatura: dict) -> list[dict]:
    """Aplica todas as regras de validação a uma fatura extraída."""
    problemas = []

    def registrar(regra: str, detalhe: str) -> None:
        problemas.append(
            {"fatura": fatura["numero"], "regra": regra, "detalhe": detalhe}
        )

    # 1. Total declarado deve bater com a soma dos itens
    soma_itens = round(sum(item["valor_total"] for item in fatura["itens"]), 2)
    diferenca = round(fatura["total_declarado"] - soma_itens, 2)
    if abs(diferenca) > TOLERANCIA:
        registrar(
            "TOTAL_DIVERGENTE",
            f"declarado R$ {fatura['total_declarado']:.2f} x "
            f"soma dos itens R$ {soma_itens:.2f} "
            f"(diferenca R$ {diferenca:.2f})",
        )

    # 2. Valor total de cada item deve ser quantidade x valor unitário
    for item in fatura["itens"]:
        esperado = round(item["quantidade"] * item["valor_unitario"], 2)
        if abs(item["valor_total"] - esperado) > TOLERANCIA:
            registrar(
                "ITEM_CALCULO_INCORRETO",
                f"{item['codigo']}: total R$ {item['valor_total']:.2f} x "
                f"esperado R$ {esperado:.2f}",
            )

    # 3. CNPJ deve ter dígitos verificadores válidos
    if not validar_cnpj(fatura["cnpj"]):
        registrar("CNPJ_INVALIDO", fatura["cnpj"])

    # 4. Datas devem ser válidas e vencimento não pode anteceder a emissão
    try:
        emissao = datetime.strptime(fatura["data_emissao"], "%d/%m/%Y")
        vencimento = datetime.strptime(fatura["data_vencimento"], "%d/%m/%Y")
        if vencimento < emissao:
            registrar(
                "VENCIMENTO_ANTERIOR_EMISSAO",
                f"emissao {fatura['data_emissao']} x "
                f"vencimento {fatura['data_vencimento']}",
            )
    except ValueError:
        registrar(
            "DATA_INVALIDA",
            f"emissao '{fatura['data_emissao']}' / "
            f"vencimento '{fatura['data_vencimento']}'",
        )

    # 5. Fatura deve ter ao menos um item
    if not fatura["itens"]:
        registrar("SEM_ITENS", "nenhum item extraido da fatura")

    return problemas


def validar_duplicidade(faturas: list[dict]) -> list[dict]:
    """Verifica números de fatura repetidos no lote."""
    problemas = []
    vistos = set()
    for fatura in faturas:
        if fatura["numero"] in vistos:
            problemas.append(
                {
                    "fatura": fatura["numero"],
                    "regra": "NUMERO_DUPLICADO",
                    "detalhe": f"numero repetido no arquivo {fatura['arquivo']}",
                }
            )
        vistos.add(fatura["numero"])
    return problemas
