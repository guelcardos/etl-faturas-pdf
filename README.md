# 📄 ETL de Faturas em PDF

Pipeline em Python que **extrai, valida e consolida dados de faturas de fornecedores em PDF**, transformando documentos não estruturados em bases prontas para análise (Excel, CSV e SQLite).

> ⚠️ Todos os dados deste projeto são **100% fictícios**, gerados pelo próprio repositório. Nenhuma informação real de empresas ou fornecedores foi utilizada.

## 🎯 O problema

Em áreas como Suprimentos e Financeiro, é comum receber faturas de dezenas de fornecedores — cada um com seu próprio layout de documento. Digitar esses dados manualmente é lento e sujeito a erro.

Este projeto simula esse cenário: **60 faturas em PDF, emitidas por 6 fornecedores fictícios em 2 layouts diferentes**, processadas de ponta a ponta por um pipeline automatizado.

## ⚙️ O que o pipeline faz

```
PDFs (não estruturados)
      │
      ▼
1. EXTRAÇÃO ──── detecta o layout de cada fatura e aplica a estratégia adequada:
      │          • Layout A: tabelas com grade → pdfplumber extract_tables
      │          • Layout B: texto corrido → expressões regulares
      ▼
2. VALIDAÇÃO ─── aplica regras de consistência:
      │          • total declarado × soma dos itens
      │          • quantidade × valor unitário de cada item
      │          • dígitos verificadores do CNPJ
      │          • datas válidas e vencimento ≥ emissão
      │          • números de fatura duplicados
      ▼
3. CONSOLIDAÇÃO ─ padroniza fornecedores, converte datas e estrutura
      │           os dados em tabelas de faturas e itens (pandas)
      ▼
4. EXPORTAÇÃO ── Excel (3 abas) + CSV + banco SQLite
```

### Exemplo de saída no terminal

```
Extraindo 60 arquivos de dados/pdfs...
------------------------------------------------------------
RESUMO DO PROCESSAMENTO
------------------------------------------------------------
Faturas extraidas:        60
Arquivos com falha:       0
Itens consolidados:       346
Inconsistencias:          4
  - TOTAL_DIVERGENTE: 4
Valor total do lote:      R$ 245,923.30
Tempo de execucao:        0.7s
```

As 4 inconsistências encontradas **não são falhas do pipeline**: o gerador cria propositalmente 4 faturas com total divergente, simulando erros de digitação do fornecedor — e a etapa de validação as detecta.

## 🚀 Como executar

```bash
# 1. Clone o repositório e instale as dependências
pip install -r requirements.txt

# 2. Gere as faturas fictícias em PDF
python src/gerar_faturas.py

# 3. Execute o pipeline de ETL
python src/pipeline.py
```

Os resultados ficam em `dados/saida/`:

| Arquivo | Conteúdo |
|---|---|
| `faturas_consolidadas.xlsx` | Abas **Faturas**, **Itens** e **Inconsistências** |
| `faturas.csv` / `itens.csv` / `inconsistencias.csv` | Mesmos dados em CSV (separador `;`) |
| `faturas.db` | Banco SQLite com as três tabelas |

## 📁 Estrutura do projeto

```
etl-faturas-pdf/
├── src/
│   ├── gerar_faturas.py   # gera as faturas fictícias (2 layouts, erros plantados)
│   ├── extracao.py        # detecção de layout e extração dos dados
│   ├── validacao.py       # regras de validação (totais, CNPJ, datas, duplicidade)
│   └── pipeline.py        # orquestra: extrai → valida → consolida → exporta
├── dados/
│   ├── pdfs/              # faturas em PDF (entrada)
│   └── saida/             # Excel, CSV e SQLite (saída)
├── requirements.txt
└── README.md
```

## 🛠️ Tecnologias

- **Python 3.10+**
- **pdfplumber** — extração de texto e tabelas de PDFs
- **pandas** — consolidação e transformação dos dados
- **reportlab** — geração das faturas fictícias
- **openpyxl** — exportação para Excel
- **sqlite3** — persistência em banco de dados

## 💡 Decisões de projeto

- **Dois layouts de fatura**: fornecedores reais não seguem um padrão único. O extrator detecta o layout pelo título do documento e aplica a estratégia adequada (tabelas × regex) — a parte mais trabalhosa de qualquer extração de PDF na vida real.
- **Erros plantados**: o gerador cria faturas com totais divergentes de propósito, para demonstrar que a camada de validação funciona (e não apenas "passa" em dados perfeitos).
- **CNPJs com dígitos verificadores válidos**: mesmo fictícios, os CNPJs são gerados com o algoritmo oficial de verificação — e o validador confere os dígitos na volta.
- **Tolerância a falhas**: um PDF corrompido ou com layout desconhecido não derruba o lote; a falha é registrada e o processamento continua.

---

Desenvolvido por **Miguel Cardoso** · [LinkedIn](https://www.linkedin.com/in/guelcardoso/) · [GitHub](https://github.com/guelcardos)
