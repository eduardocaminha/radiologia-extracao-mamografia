# Databricks notebook source
# MAGIC %md
# MAGIC # Processar CSV de Mamografias - Produção
# MAGIC 
# MAGIC **Notebook para processamento em lote de laudos de mamografia**
# MAGIC 
# MAGIC Este notebook processa CSVs completos usando:
# MAGIC - **Databricks Foundation Models** (serving endpoints)
# MAGIC - **Spark UDFs** para processamento paralelo
# MAGIC - **Delta Tables** para armazenamento estruturado
# MAGIC 
# MAGIC **Performance:**
# MAGIC - Llama 3.1 8B: ~300-350 laudos/minuto (~5-6/segundo)
# MAGIC - Llama 3.3 70B: ~60-120 laudos/minuto (~1-2/segundo)
# MAGIC 
# MAGIC **Output:** Delta Table com laudos estruturados + análises de qualidade

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Configuração

# COMMAND ----------

# CONFIGURAÇÕES - AJUSTAR ANTES DE EXECUTAR
CSV_PATH = "/caminho/para/seu/arquivo.csv"  # ← AJUSTAR
OUTPUT_TABLE = "seu_catalog.seu_schema.mamografia_estruturada"  # ← AJUSTAR

# Modelo
ENDPOINT_NAME = "databricks-meta-llama-3-1-8b-instruct"  # ou databricks-meta-llama-3-3-70b-instruct
TEMPERATURE = 0.1
MAX_TOKENS = 4096

# Processamento
BATCH_SIZE = 100  # Processar em lotes de N laudos

# Paths (ajustar se necessário)
TEMPLATE_PATH = "/Workspace/Repos/innovation/radiologia-extracao-mamografia/config/template.json"
PROMPT_PATH = "/Workspace/Repos/innovation/radiologia-extracao-mamografia/config/prompt_extracao_mamografia.md"

print("=" * 80)
print("CONFIGURAÇÃO")
print("=" * 80)
print(f"CSV Input: {CSV_PATH}")
print(f"Output Table: {OUTPUT_TABLE}")
print(f"Endpoint: {ENDPOINT_NAME}")
print(f"Batch size: {BATCH_SIZE}")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Carregar Template e Prompt

# COMMAND ----------

import json

# Carregar template
with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
    template = json.load(f)

# Carregar prompt
with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
    prompt_instructions = f.read()

print("✅ Template e prompt carregados")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Carregar CSV

# COMMAND ----------

# Ler CSV
df_laudos = spark.read.csv(
    CSV_PATH,
    header=True,
    inferSchema=True,
    encoding="UTF-8"
)

print(f"✅ CSV carregado: {df_laudos.count()} registros")
print(f"\nColunas: {df_laudos.columns}")
print("\nSchema:")
df_laudos.printSchema()

# Preview
display(df_laudos.limit(3))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Criar Função de Estruturação

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
import json
import time

def estruturar_laudo_producao(texto_laudo: str) -> str:
    """
    Estrutura laudo usando Databricks endpoint
    Retorna JSON string (para compatibilidade com UDF)
    """
    if not texto_laudo or texto_laudo.strip() == "":
        return json.dumps({
            "sucesso": False,
            "erro": "Laudo vazio"
        })
    
    try:
        w = WorkspaceClient()
        
        # Criar prompt
        prompt_completo = f"""{prompt_instructions}

---

LAUDO A SER ESTRUTURADO:

{texto_laudo}

---

Retorne APENAS o JSON estruturado (sem texto antes ou depois):
"""
        
        messages = [
            ChatMessage(
                role=ChatMessageRole.SYSTEM,
                content="Você é um assistente especializado em estruturação de laudos de mamografia. Retorne APENAS JSON válido seguindo o template fornecido."
            ),
            ChatMessage(
                role=ChatMessageRole.USER,
                content=prompt_completo
            )
        ]
        
        # Chamar endpoint
        response = w.serving_endpoints.query(
            name=ENDPOINT_NAME,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE
        )
        
        response_text = response.choices[0].message.content
        
        # Extrair JSON
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx == -1 or end_idx <= start_idx:
            return json.dumps({
                "sucesso": False,
                "erro": "JSON não encontrado na resposta"
            })
        
        json_str = response_text[start_idx:end_idx]
        
        # Validar JSON
        laudo_estruturado = json.loads(json_str)
        
        # Retornar como string JSON válida
        return json.dumps({
            "sucesso": True,
            "laudo_estruturado": laudo_estruturado,
            "modelo": ENDPOINT_NAME
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "sucesso": False,
            "erro": f"{type(e).__name__}: {str(e)}"
        }, ensure_ascii=False)

# Testar função
teste = estruturar_laudo_producao("MAMOGRAFIA: BI-RADS 1. ACR B. Sem alterações.")
print("✅ Função criada")
print(f"Teste: {teste[:200]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Criar UDF Spark

# COMMAND ----------

from pyspark.sql.functions import udf
from pyspark.sql.types import StringType

# Criar UDF
estruturar_udf = udf(estruturar_laudo_producao, StringType())

print("✅ UDF criada: estruturar_udf")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Processar Laudos

# COMMAND ----------

from pyspark.sql.functions import col, current_timestamp, from_json, lit
from pyspark.sql.types import StructType, StructField, StringType, BooleanType

# Schema do resultado
resultado_schema = StructType([
    StructField("sucesso", BooleanType(), True),
    StructField("laudo_estruturado", StringType(), True),
    StructField("modelo", StringType(), True),
    StructField("erro", StringType(), True)
])

print("Processando laudos...")
print("=" * 80)

# Aplicar UDF (ajustar nome da coluna conforme seu CSV)
df_processado = df_laudos.withColumn(
    "resultado_json",
    estruturar_udf(col("DS_LAUDO_MEDICO"))  # ← Ajustar nome da coluna
).withColumn(
    "dt_processamento",
    current_timestamp()
)

# Parsear resultado JSON
df_processado = df_processado.withColumn(
    "resultado",
    from_json(col("resultado_json"), resultado_schema)
)

# Extrair campos
df_processado = df_processado \
    .withColumn("processamento_sucesso", col("resultado.sucesso")) \
    .withColumn("laudo_estruturado", col("resultado.laudo_estruturado")) \
    .withColumn("modelo_llm", col("resultado.modelo")) \
    .withColumn("erro_processamento", col("resultado.erro")) \
    .drop("resultado_json", "resultado")

# Cache (importante para processamento em lote)
df_processado.cache()

# Forçar execução
total_processado = df_processado.count()

print(f"✅ {total_processado} laudos processados")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Extrair Campos Chave do JSON

# COMMAND ----------

from pyspark.sql.functions import get_json_object, size, split

# Extrair campos principais do JSON estruturado
df_final = df_processado.withColumn(
    "birads",
    get_json_object(col("laudo_estruturado"), "$.categorias_diagnosticas_conclusao_laudo.categoria_birads")
).withColumn(
    "acr",
    get_json_object(col("laudo_estruturado"), "$.padrao_parenquimatoso.classificacao_ACR")
).withColumn(
    "num_achados",
    size(split(get_json_object(col("laudo_estruturado"), "$.descricao_achados"), ","))
).withColumn(
    "lateralidade",
    get_json_object(col("laudo_estruturado"), "$.tecnica.lateralidade")
).withColumn(
    "comparacao_disponivel",
    get_json_object(col("laudo_estruturado"), "$.comparacao_exames_previos.disponivel")
)

print("✅ Campos chave extraídos")
display(df_final.select("CD_ATENDIMENTO", "birads", "acr", "num_achados", "processamento_sucesso").limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Salvar em Delta Table

# COMMAND ----------

# Salvar (mode="overwrite" para primeira vez, "append" para adicionar)
df_final.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(OUTPUT_TABLE)

print(f"✅ Dados salvos em: {OUTPUT_TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Análises de Qualidade

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Estatísticas gerais
# MAGIC SELECT 
#MAGIC     COUNT(*) as total_laudos,
#MAGIC     SUM(CASE WHEN processamento_sucesso THEN 1 ELSE 0 END) as sucessos,
#MAGIC     ROUND(SUM(CASE WHEN processamento_sucesso THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as taxa_sucesso_pct,
#MAGIC     COUNT(DISTINCT birads) as birads_distintos,
#MAGIC     COUNT(DISTINCT acr) as acr_distintos
# MAGIC FROM ${OUTPUT_TABLE}

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Distribuição BI-RADS
# MAGIC SELECT 
#MAGIC     birads,
#MAGIC     COUNT(*) as quantidade,
#MAGIC     ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentual
# MAGIC FROM ${OUTPUT_TABLE}
# MAGIC WHERE processamento_sucesso = true
# MAGIC GROUP BY birads
# MAGIC ORDER BY birads

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Distribuição ACR (densidade mamária)
# MAGIC SELECT 
#MAGIC     acr,
#MAGIC     COUNT(*) as quantidade,
#MAGIC     ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentual
# MAGIC FROM ${OUTPUT_TABLE}
# MAGIC WHERE processamento_sucesso = true
# MAGIC GROUP BY acr
# MAGIC ORDER BY acr

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Distribuição de achados
# MAGIC SELECT 
#MAGIC     CASE 
#MAGIC         WHEN num_achados = 0 THEN 'Sem achados'
#MAGIC         WHEN num_achados = 1 THEN '1 achado'
#MAGIC         WHEN num_achados BETWEEN 2 AND 3 THEN '2-3 achados'
#MAGIC         ELSE '4+ achados'
#MAGIC     END as categoria_achados,
#MAGIC     COUNT(*) as quantidade,
#MAGIC     ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentual
# MAGIC FROM ${OUTPUT_TABLE}
# MAGIC WHERE processamento_sucesso = true
# MAGIC GROUP BY 1
# MAGIC ORDER BY quantidade DESC

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Casos suspeitos (BI-RADS 4 e 5)
# MAGIC SELECT 
#MAGIC     CD_ATENDIMENTO,
#MAGIC     birads,
#MAGIC     acr,
#MAGIC     num_achados,
#MAGIC     dt_processamento
# MAGIC FROM ${OUTPUT_TABLE}
# MAGIC WHERE birads IN ('4', '5')
#MAGIC     AND processamento_sucesso = true
# MAGIC ORDER BY birads DESC, dt_processamento DESC
# MAGIC LIMIT 20

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Erros de processamento
# MAGIC SELECT 
#MAGIC     erro_processamento,
#MAGIC     COUNT(*) as quantidade
# MAGIC FROM ${OUTPUT_TABLE}
# MAGIC WHERE processamento_sucesso = false
# MAGIC GROUP BY erro_processamento
# MAGIC ORDER BY quantidade DESC

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Visualizações

# COMMAND ----------

# Distribuição BI-RADS (gráfico)
df_birads = spark.sql(f"""
    SELECT birads, COUNT(*) as quantidade
    FROM {OUTPUT_TABLE}
    WHERE processamento_sucesso = true
    GROUP BY birads
    ORDER BY birads
""")

display(df_birads)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📊 Resumo da Execução
# MAGIC 
# MAGIC **Próximos passos:**
# MAGIC 
# MAGIC 1. **Validação médica:** Revisar amostra de laudos estruturados
# MAGIC 2. **Casos críticos:** Revisar todos BI-RADS 4 e 5
# MAGIC 3. **Erros:** Investigar laudos com falha no processamento
# MAGIC 4. **Reprocessamento:** Se necessário, reprocessar apenas erros
# MAGIC 
# MAGIC **Queries úteis:**
# MAGIC 
# MAGIC ```sql
# MAGIC -- Exportar casos suspeitos
# MAGIC SELECT * 
# MAGIC FROM ${OUTPUT_TABLE}
# MAGIC WHERE birads IN ('4', '5')
# MAGIC 
# MAGIC -- Buscar por texto no laudo original
# MAGIC SELECT CD_ATENDIMENTO, DS_LAUDO_MEDICO, birads
# MAGIC FROM ${OUTPUT_TABLE}
# MAGIC WHERE DS_LAUDO_MEDICO LIKE '%calcificações%'
# MAGIC 
# MAGIC -- JSON completo de um laudo específico
# MAGIC SELECT laudo_estruturado
# MAGIC FROM ${OUTPUT_TABLE}
# MAGIC WHERE CD_ATENDIMENTO = 'SEU_ID'
# MAGIC ```

