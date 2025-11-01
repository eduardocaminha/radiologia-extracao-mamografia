# Notebooks - Processamento de Laudos

## ✨ Sem Setup Necessário!

Estes notebooks usam **Databricks Foundation Models** (serving endpoints) que já estão instalados e prontos para uso.

Não precisa baixar modelos, instalar bibliotecas ou configurar GPU/CPU. É só executar!

## 📋 Notebooks Disponíveis

### 1. `01_processar_laudos.py` 🧪
**Teste e desenvolvimento** - Processar laudos individuais ou pequenos lotes

**Uso:**
- Testar estruturação com laudos de exemplo
- Debug e validação de qualidade
- Ajustar prompts e parâmetros
- Comparar diferentes modelos (Llama 8B vs 70B)

**Sem pré-requisitos!** Apenas execute.

**Tempo por laudo:**
- Llama 3.1 8B: ~0.2s
- Llama 3.3 70B: ~0.8s

### 2. `02_processar_csv_mamografia.py` ⭐
**Produção** - Processar CSVs completos em lote com Spark

**Uso:**
- Processar milhares de laudos de uma vez
- Salvar em Delta Table estruturada
- Análises automáticas de qualidade
- Dashboards e visualizações

**Sem pré-requisitos!** Apenas configure paths e execute.

**Performance:**
- 300-350 laudos/minuto (Llama 3.1 8B)
- 60-120 laudos/minuto (Llama 3.3 70B)

**Input:** CSV com colunas:
- `CD_ATENDIMENTO` (obrigatório)
- `DS_LAUDO_MEDICO` (obrigatório)
- `NM_PROCEDIMENTO` (recomendado)
- `CD_OCORRENCIA` (opcional)
- `CD_ORDEM` (opcional)
- `CD_PROCEDIMENTO` (opcional)
- `DT_PROCEDIMENTO_REALIZADO` (opcional)

**Output:** Delta Table com:
- Laudo original
- Laudo estruturado (JSON)
- Metadados extraídos (BI-RADS, ACR, achados)
- Métricas de confiança
- Anotações da LLM
- Erros de validação (se houver)

## 🚀 Como Usar

### Passo a Passo Rápido

1. **Clonar repositório no Databricks**
```bash
%sh
cd /Workspace/Repos/<seu_usuario>/
git clone https://github.com/eduardocaminha/radiologia-extracao-mamografia.git
```

2. **Abrir e configurar `02_processar_csv_mamografia.py`**
```python
# Seção 1: Configuração
CSV_PATH = "/seu/caminho/para/laudos.csv"
OUTPUT_TABLE = "seu_catalog.seu_schema.mamografia_estruturada"
ENDPOINT_NAME = "databricks-meta-llama-3-1-8b-instruct"
```

3. **Executar tudo**
```
Run All (Ctrl + Shift + Enter)
```

**Pronto!** Não precisa de setup prévio.

---

### Teste Rápido (Opcional)

Antes de processar CSV completo, teste com `01_processar_laudos.py`:

1. Abrir notebook
2. Seção 4: Cole seu laudo de teste
3. Executar células 1-6
4. Ver JSON estruturado na saída

### Output

O notebook gera:

#### Tabela Delta com colunas:
- **Originais:** `cd_atendimento`, `texto_original`, `nm_procedimento`, etc
- **Estruturadas:** `laudo_estruturado` (JSON completo)
- **Extraídas:** `birads`, `acr`, `num_achados`
- **Qualidade:** `confianca_media`, `confianca_minima`, `tem_erros_validacao`
- **Metadados:** `processamento_sucesso`, `processamento_timestamp`, `modelo_llm`

#### Análises automáticas:
1. Estatísticas gerais (taxa de sucesso, confiança)
2. Distribuição BI-RADS
3. Distribuição ACR (densidade mamária)
4. Distribuição de achados
5. Casos de baixa confiança (<0.7)
6. Erros de processamento

## 📊 Queries Úteis

### Consultar laudos processados
```sql
SELECT 
    cd_atendimento,
    birads,
    acr,
    num_achados,
    confianca_media,
    laudo_estruturado
FROM seu_catalog.seu_schema.mamografia_estruturada
WHERE dt_processamento = CURRENT_DATE
    AND processamento_sucesso = true
    AND birads IN ('4', '5')
```

### Extrair achados específicos
```sql
SELECT 
    cd_atendimento,
    birads,
    get_json_object(laudo_estruturado, '$.descricao_achados') as achados
FROM seu_catalog.seu_schema.mamografia_estruturada
WHERE num_achados > 0
```

### Casos para revisão médica
```sql
SELECT *
FROM seu_catalog.seu_schema.mamografia_estruturada
WHERE birads IN ('4', '5')
    OR confianca_media < 0.7
    OR tem_erros_validacao = true
ORDER BY birads DESC, confianca_media ASC
```

## 🔧 Troubleshooting

### Erro: "Endpoint não encontrado"
```python
# Listar endpoints disponíveis
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
for endpoint in w.serving_endpoints.list():
    print(f"- {endpoint.name}")
```

Se o endpoint não existir, use um alternativo:
- `databricks-meta-llama-3-1-8b-instruct`
- `databricks-mistral-7b-instruct-v0-2`

### Erro: "JSON inválido"
Verifique:
1. Template (`config/template.json`) está acessível
2. Prompt (`config/prompt_extracao_mamografia.md`) está completo
3. Laudo não está vazio

### Performance lenta
- **Llama 8B** já é o mais rápido (~5-6 laudos/s)
- Processar em horários de menor carga do cluster
- Dividir CSV em lotes menores

### Validação falhou
```python
# Ver casos com erro
df_erros = spark.sql(f"""
    SELECT CD_ATENDIMENTO, erro_processamento, DS_LAUDO_MEDICO
    FROM {OUTPUT_TABLE}
    WHERE processamento_sucesso = false
    LIMIT 10
""")
display(df_erros)
```

## 📈 Performance Real (Testada)

| Modelo | Endpoint | Laudos/min | Latência | Uso |
|--------|----------|-----------|----------|-----|
| Llama 3.1 8B | databricks-meta-llama-3-1-8b-instruct | 300-350 | 0.17s | ✅ **Recomendado** |
| Llama 3.3 70B | databricks-meta-llama-3-3-70b-instruct | 60-120 | 0.80s | Alta precisão |
| Mistral 7B | databricks-mistral-7b-instruct-v0-2 | 200-250 | 0.24s | Alternativa |

**Cluster testado:** ARM64 CPU (Standard_D8pds_v6) - 8 cores, 32GB RAM

**Exemplo real:** 10.000 laudos
- Llama 3.1 8B: ~30-35 minutos
- Llama 3.3 70B: ~80-165 minutos

## 📝 Validação de Qualidade

Após processar, sempre:

1. **Verificar taxa de sucesso** (alvo: >95%)
2. **Revisar confiança média** (alvo: >0.85)
3. **Analisar casos de baixa confiança**
4. **Validar amostra com médicos** (20-50 laudos)
5. **Revisar todos BI-RADS 4 e 5**

## 🔄 Reprocessamento

Para reprocessar laudos com erros:
```python
# Filtrar apenas erros do dia
df_erros = spark.sql("""
    SELECT cd_atendimento, texto_original
    FROM seu_catalog.seu_schema.mamografia_estruturada
    WHERE dt_processamento = CURRENT_DATE
        AND processamento_sucesso = false
""")

# Reprocessar (adaptar código da seção 6)
```

## 📧 Suporte

Para dúvidas ou issues:
- GitHub: https://github.com/eduardocaminha/radiologia-extracao-mamografia/issues

