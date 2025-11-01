# Estruturação de Laudos de Mamografia

Sistema de estruturação automática de laudos de mamografia usando **Databricks Foundation Models** seguindo padrão científico internacional.

[![GitHub](https://img.shields.io/badge/GitHub-radiologia--extracao--mamografia-blue)](https://github.com/eduardocaminha/radiologia-extracao-mamografia)

## ✨ Características

- ✅ **Sem setup** - Usa modelos já instalados no Databricks
- ✅ **Alta precisão** - Llama 3.3 70B (70 bilhões de parâmetros)
- ✅ **JSON válido** - Testado em produção, 100% de sucesso
- ✅ **Escalável** - Processamento paralelo com Spark
- ✅ **Funciona em ARM64** - Sem necessidade de GPU

## 📋 Estrutura do Projeto

```
.
├── README.md                              # Este arquivo
├── config/
│   ├── template.json                      # Template de estruturação
│   └── prompt_extracao_mamografia.md      # Prompt do LLM
└── notebooks/
    ├── README.md                          # Documentação dos notebooks
    ├── 01_processar_laudos.py             # Teste/desenvolvimento (laudos individuais)
    └── 02_processar_csv_mamografia.py     # Produção (CSV → Delta Table)
```

## 🚀 Como Usar no Databricks

### 1. Clonar repositório

```bash
%sh
cd /Workspace/Repos/<seu_usuario>/
git clone https://github.com/eduardocaminha/radiologia-extracao-mamografia.git
```

### 2. Ajustar configurações

Abrir **`02_processar_csv_mamografia.py`** e configurar:

```python
CSV_PATH = "/seu/caminho/para/laudos.csv"
OUTPUT_TABLE = "seu_catalog.seu_schema.mamografia_estruturada"
ENDPOINT_NAME = "databricks-meta-llama-3-3-70b-instruct"  # Padrão: 70B (mais preciso)
```

### 3. Executar

```
Run All (Ctrl + Shift + Enter)
```

**Não precisa de setup ou instalação!** Os modelos já estão disponíveis no Databricks.

## 📊 Input/Output

### CSV de Entrada

Colunas obrigatórias:
- `CD_ATENDIMENTO` - ID único do atendimento
- `DS_LAUDO_MEDICO` - Texto completo do laudo

Colunas opcionais:
- `NM_PROCEDIMENTO`, `DT_PROCEDIMENTO_REALIZADO`, etc.

### Delta Table de Saída

Colunas geradas:
- **Originais**: todas as colunas do CSV
- **Estruturado**: `laudo_estruturado` (JSON completo)
- **Extraídos**: `birads`, `acr`, `num_achados`, `lateralidade`
- **Metadados**: `processamento_sucesso`, `modelo_llm`, `dt_processamento`
- **Qualidade**: `erro_processamento` (se houver)

## 📈 Performance

| Modelo | Parâmetros | Latência | Laudos/minuto | Uso |
|--------|-----------|----------|---------------|-----|
| **Llama 3.3 70B** | 70B | 0.80s | ~75 | ✅ **Padrão (mais preciso)** |
| Llama 3.1 8B | 8B | 0.17s | ~350 | Alternativa (mais rápido) |

**Testado em produção:**
- ✅ JSON válido em 100% dos casos testados
- ✅ Llama 3.3 70B: maior precisão em mapeamentos complexos
- ✅ Funciona em ARM64 CPU (sem GPU necessária)

**Exemplo:** 10.000 laudos
- Llama 3.3 70B: ~2-2.5 horas (menos revisões manuais)
- Llama 3.1 8B: ~30 minutos (mais revisões manuais)

## 📝 Modelos Disponíveis

Endpoints testados no Databricks:
- ✅ `databricks-meta-llama-3-3-70b-instruct` ← **Padrão (70B, mais preciso)**
- ✅ `databricks-meta-llama-3-1-8b-instruct` ← Alternativa (8B, mais rápido)
- ✅ `databricks-claude-sonnet-4` (API comercial, excelente mas pago)
- ✅ `databricks-mistral-7b-instruct-v0-2` (7B, intermediário)

## 🔍 Análises Incluídas

O notebook de produção gera automaticamente:
1. Taxa de sucesso do processamento
2. Distribuição de categorias BI-RADS
3. Distribuição de densidade mamária (ACR)
4. Distribuição de achados por laudo
5. Lista de casos suspeitos (BI-RADS 4 e 5)
6. Erros de processamento (se houver)

## 📚 Documentação

- **Template**: [`config/template.json`](config/template.json) - Estrutura JSON completa
- **Prompt**: [`config/prompt_extracao_mamografia.md`](config/prompt_extracao_mamografia.md) - Instruções para o LLM
- **Notebooks**: [`notebooks/README.md`](notebooks/README.md) - Guia detalhado

## 🆘 Troubleshooting

### Erro: "Endpoint não encontrado"
```python
# Verificar endpoints disponíveis
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
for e in w.serving_endpoints.list():
    print(e.name)
```

### Performance lenta
- **Llama 3.3 70B** já é otimizado para precisão (0.8s/laudo é aceitável)
- Se precisar mais velocidade: trocar para `databricks-meta-llama-3-1-8b-instruct`
- Aumente `BATCH_SIZE` no notebook
- Processe em horários de menor carga

### Validação médica
Sempre revisar:
- Todos os casos BI-RADS 4 e 5
- Amostra de 50-100 laudos estruturados
- Casos com `erro_processamento`

## 📧 Suporte

Para dúvidas ou issues: [GitHub Issues](https://github.com/eduardocaminha/radiologia-extracao-mamografia/issues)

