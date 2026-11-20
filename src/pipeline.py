"""
Pipeline de ETL: extrai os dados das faturas em PDF, valida,
consolida e exporta para Excel, CSV e SQLite.

Uso:
    python src/pipeline.py
"""

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from extracao import extrair_fatura
from validacao import validar_duplicidade, validar_fatura

PASTA_PDFS = Path(__file__).resolve().parent.parent / "dados" / "pdfs"
PASTA_SAIDA = Path(__file__).resolve().parent.parent / "dados" / "saida"


# ---------------------------------------------------------------------------
# Extração
# ---------------------------------------------------------------------------

def extrair_todas(pasta: Path) -> tuple[list[dict], list[dict]]:
    """Extrai todas as faturas da pasta. Devolve (faturas, falhas)."""
    faturas, falhas = [], []
    arquivos = sorted(pasta.glob("*.pdf"))
    print(f"Extraindo {len(arquivos)} arquivos de {pasta}...")

    for caminho in arquivos:
        try:
            faturas.append(extrair_fatura(caminho))
        except Exception as erro:  # arquivo corrompido, layout desconhecido etc.
            falhas.append({"arquivo": caminho.name, "erro": str(erro)})

    return faturas, falhas


# ---------------------------------------------------------------------------
# Consolidação
# ---------------------------------------------------------------------------

def montar_dataframes(faturas: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Transforma a lista de faturas em DataFrames de cabeçalho e itens."""
    df_faturas = pd.DataFrame(
        [
            {
                "numero": f["numero"],
                "fornecedor": f["fornecedor"],
                "cnpj": f["cnpj"],
                "data_emissao": f["data_emissao"],
                "data_vencimento": f["data_vencimento"],
                "condicao_pagamento": f["condicao_pagamento"],
                "qtd_itens": len(f["itens"]),
                "total_declarado": f["total_declarado"],
                "layout": f["layout"],
                "arquivo": f["arquivo"],
            }
            for f in faturas
        ]
    )

    df_itens = pd.DataFrame(
        [
            {"numero_fatura": f["numero"], **item}
            for f in faturas
            for item in f["itens"]
        ]
    )

    # padronização: nomes de fornecedor em maiúsculas (os layouts
    # divergem na capitalização) e datas em formato datetime
    df_faturas["fornecedor"] = df_faturas["fornecedor"].str.upper()
    for coluna in ("data_emissao", "data_vencimento"):
        df_faturas[coluna] = pd.to_datetime(df_faturas[coluna], format="%d/%m/%Y")

    return df_faturas.sort_values("numero"), df_itens


# ---------------------------------------------------------------------------
# Exportação
# ---------------------------------------------------------------------------

def exportar(
    df_faturas: pd.DataFrame,
    df_itens: pd.DataFrame,
    df_problemas: pd.DataFrame,
    pasta: Path,
) -> None:
    """Grava os resultados em Excel, CSV e SQLite."""
    pasta.mkdir(parents=True, exist_ok=True)

    # Excel com três abas
    with pd.ExcelWriter(pasta / "faturas_consolidadas.xlsx") as escritor:
        df_faturas.to_excel(escritor, sheet_name="Faturas", index=False)
        df_itens.to_excel(escritor, sheet_name="Itens", index=False)
        df_problemas.to_excel(escritor, sheet_name="Inconsistencias", index=False)

    # CSVs individuais
    df_faturas.to_csv(pasta / "faturas.csv", index=False, sep=";")
    df_itens.to_csv(pasta / "itens.csv", index=False, sep=";")
    df_problemas.to_csv(pasta / "inconsistencias.csv", index=False, sep=";")

    # Banco SQLite
    with sqlite3.connect(pasta / "faturas.db") as conexao:
        df_faturas.to_sql("faturas", conexao, if_exists="replace", index=False)
        df_itens.to_sql("itens", conexao, if_exists="replace", index=False)
        df_problemas.to_sql(
            "inconsistencias", conexao, if_exists="replace", index=False
        )


# ---------------------------------------------------------------------------
# Execução do pipeline
# ---------------------------------------------------------------------------

def executar() -> None:
    inicio = datetime.now()

    # 1. Extração
    faturas, falhas = extrair_todas(PASTA_PDFS)

    # 2. Validação
    problemas = []
    for fatura in faturas:
        problemas.extend(validar_fatura(fatura))
    problemas.extend(validar_duplicidade(faturas))
    df_problemas = pd.DataFrame(problemas, columns=["fatura", "regra", "detalhe"])

    # 3. Consolidação
    df_faturas, df_itens = montar_dataframes(faturas)

    # 4. Exportação
    exportar(df_faturas, df_itens, df_problemas, PASTA_SAIDA)

    # 5. Resumo no terminal
    duracao = (datetime.now() - inicio).total_seconds()
    print("-" * 60)
    print("RESUMO DO PROCESSAMENTO")
    print("-" * 60)
    print(f"Faturas extraidas:        {len(faturas)}")
    print(f"Arquivos com falha:       {len(falhas)}")
    print(f"Itens consolidados:       {len(df_itens)}")
    print(f"Inconsistencias:          {len(df_problemas)}")
    if not df_problemas.empty:
        for regra, qtd in df_problemas["regra"].value_counts().items():
            print(f"  - {regra}: {qtd}")
    print(f"Valor total do lote:      R$ {df_faturas['total_declarado'].sum():,.2f}")
    print(f"Tempo de execucao:        {duracao:.1f}s")
    print(f"Arquivos gerados em:      {PASTA_SAIDA}")

    if falhas:
        print("\nFalhas de extracao:")
        for falha in falhas:
            print(f"  - {falha['arquivo']}: {falha['erro']}")


if __name__ == "__main__":
    executar()
