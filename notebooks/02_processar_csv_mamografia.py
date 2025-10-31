# Databricks notebook source
# MAGIC %md
# MAGIC # Estruturação de Laudos de Mamografia - CSV Input
# MAGIC 
# MAGIC Processa laudos de mamografia a partir de CSV e estrutura usando Phi-4
# MAGIC 
# MAGIC **Input**: CSV com colunas:
# MAGIC - `CD_ATENDIMENTO`
# MAGIC - `DS_LAUDO_MEDICO`
# MAGIC - `NM_PROCEDIMENTO`
# MAGIC - `CD_OCORRENCIA` (opcional)
# MAGIC - `CD_ORDEM` (opcional)
# MAGIC - `CD_PROCEDIMENTO` (opcional)
# MAGIC - `DT_PROCEDIMENTO_REALIZADO` (opcional)
# MAGIC 
# MAGIC **Output**: Delta Table com laudos estruturados

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Setup e Configuração

# COMMAND ----------

import sys
sys.path.append("/Workspace/Users/seu_usuario/radiologia-extracao-mamografia")

from src.extractor import LaudoExtractor
from src.validators import validar_laudo_estruturado, calcular_metricas_confianca, extrair_anotacoes_llm
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, FloatType, IntegerType, BooleanType
from datetime import datetime
import json
import pandas as pd
import hashlib

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Parâmetros

# COMMAND ----------

# CONFIGURAR AQUI
CSV_PATH = "/Workspace/Innovation/t_eduardo.caminha/radiologia-extracao-laudos/outputs/laudos_2020-09_2020-10.csv"
OUTPUT_TABLE = "seu_catalog.seu_schema.mamografia_estruturada"
BATCH_SIZE = 100  # Processar em lotes

print(f"📂 CSV: {CSV_PATH}")
print(f"📊 Tabela destino: {OUTPUT_TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Inicializar Extrator Phi-4
# MAGIC 
# MAGIC ### ⚠️ Pré-requisito: Ollama + Phi-4 instalado
# MAGIC 
# MAGIC **Se ainda não instalou**, execute primeiro: `00_setup_ollama_phi4.py`

# COMMAND ----------

# Verificar Ollama
import requests
try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    if response.status_code == 200:
        modelos = [m["name"] for m in response.json()["models"]]
        print("✅ Ollama rodando")
        print(f"Modelos: {', '.join(modelos)}")
        
        if not any("phi4" in m for m in modelos):
            print("\n❌ Phi-4 não encontrado!")
            print("Execute notebook: 00_setup_ollama_phi4.py")
            dbutils.notebook.exit("Phi-4 não instalado")
    else:
        raise Exception("Ollama não está respondendo")
except Exception as e:
    print(f"❌ Erro Ollama: {e}")
    print("\n📌 Execute primeiro: 00_setup_ollama_phi4.py")
    dbutils.notebook.exit("Ollama não disponível")

# Inicializar extrator
extractor = LaudoExtractor(
    model="phi4:14b",
    template_path="/Workspace/Users/seu_usuario/radiologia-extracao-mamografia/config/template.json",
    prompt_path="/Workspace/Users/seu_usuario/radiologia-extracao-mamografia/config/prompt_extracao_mamografia.md"
)

print("✅ Extrator Phi-4 inicializado")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Carregar CSV

# COMMAND ----------

# Ler CSV via Pandas
print("📂 Carregando CSV...")

df_pandas = pd.read_csv(
    CSV_PATH,
    sep=";",
    encoding="utf-8",
    dtype=str
)

print(f"✅ CSV carregado: {len(df_pandas)} registros")
print(f"Colunas: {list(df_pandas.columns)}")

# Converter para Spark
df_csv = spark.createDataFrame(df_pandas)

# Verificar colunas necessárias
required_cols = ['CD_ATENDIMENTO', 'DS_LAUDO_MEDICO']
missing = [c for c in required_cols if c not in df_csv.columns]
if missing:
    raise ValueError(f"❌ Colunas faltando: {missing}")

display(df_csv.limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Limpeza e Filtros

# COMMAND ----------

# Filtrar apenas laudos com conteúdo mínimo
df_clean = df_csv.filter(
    (F.col("DS_LAUDO_MEDICO").isNotNull()) &
    (F.length(F.trim(F.col("DS_LAUDO_MEDICO"))) > 50)
)

# Filtrar apenas mamografias
if "NM_PROCEDIMENTO" in df_clean.columns:
    df_clean = df_clean.filter(
        F.upper(F.col("NM_PROCEDIMENTO")).contains("MAMOGRAFIA")
    )

print(f"Registros originais: {df_csv.count()}")
print(f"Após limpeza: {df_clean.count()}")
print(f"Filtrados: {df_csv.count() - df_clean.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Processamento em Lotes

# COMMAND ----------

# Coletar dados para processar
laudos_para_processar = df_clean.select(
    "CD_ATENDIMENTO",
    "DS_LAUDO_MEDICO",
    F.coalesce(F.col("NM_PROCEDIMENTO"), F.lit("MAMOGRAFIA")).alias("NM_PROCEDIMENTO"),
    F.coalesce(F.col("CD_OCORRENCIA"), F.lit(None)).alias("CD_OCORRENCIA"),
    F.coalesce(F.col("CD_ORDEM"), F.lit(None)).alias("CD_ORDEM"),
    F.coalesce(F.col("CD_PROCEDIMENTO"), F.lit(None)).alias("CD_PROCEDIMENTO"),
    F.coalesce(F.col("DT_PROCEDIMENTO_REALIZADO"), F.lit(None)).alias("DT_PROCEDIMENTO_REALIZADO")
).collect()

print(f"📊 Total de laudos a processar: {len(laudos_para_processar)}")

# COMMAND ----------

# Processar em lotes
from tqdm import tqdm

resultados_estruturados = []
erros = []

print(f"🔄 Processando {len(laudos_para_processar)} laudos...")

for i in tqdm(range(0, len(laudos_para_processar), BATCH_SIZE)):
    batch = laudos_para_processar[i:i+BATCH_SIZE]
    
    for row in batch:
        try:
            # Estruturar laudo
            resultado = extractor.processar(
                laudo_texto=row.DS_LAUDO_MEDICO,
                cd_atendimento=row.CD_ATENDIMENTO
            )
            
            # Validar
            erros_validacao = validar_laudo_estruturado(resultado, extractor.template)
            metricas = calcular_metricas_confianca(resultado)
            anotacoes = extrair_anotacoes_llm(resultado)
            
            # Adicionar metadados originais
            resultado_completo = {
                "cd_atendimento": row.CD_ATENDIMENTO,
                "cd_ocorrencia": row.CD_OCORRENCIA,
                "cd_ordem": row.CD_ORDEM,
                "cd_procedimento": row.CD_PROCEDIMENTO,
                "dt_procedimento_realizado": row.DT_PROCEDIMENTO_REALIZADO,
                "nm_procedimento": row.NM_PROCEDIMENTO,
                "texto_original": row.DS_LAUDO_MEDICO,
                "laudo_estruturado": json.dumps(resultado, ensure_ascii=False),
                "birads": resultado.get("categorias_diagnosticas_conclusao_laudo", {}).get("categoria_birads"),
                "acr": resultado.get("padrao_parenquimatoso", {}).get("classificacao_ACR"),
                "num_achados": len(resultado.get("descricao_achados", [])),
                "confianca_media": metricas["media"],
                "confianca_minima": metricas["minima"],
                "num_anotacoes_llm": len(anotacoes),
                "tem_erros_validacao": len(erros_validacao) > 0,
                "erros_validacao": json.dumps(erros_validacao, ensure_ascii=False) if erros_validacao else None,
                "hash_integridade": hashlib.md5(row.DS_LAUDO_MEDICO.encode('utf-8')).hexdigest(),
                "processamento_sucesso": True,
                "processamento_timestamp": datetime.now().isoformat()
            }
            
            resultados_estruturados.append(resultado_completo)
            
        except Exception as e:
            erro_registro = {
                "cd_atendimento": row.CD_ATENDIMENTO,
                "texto_original": row.DS_LAUDO_MEDICO,
                "processamento_sucesso": False,
                "erro_mensagem": str(e),
                "processamento_timestamp": datetime.now().isoformat()
            }
            erros.append(erro_registro)
            resultados_estruturados.append(erro_registro)

print(f"✅ Processamento concluído!")
print(f"   Sucessos: {len([r for r in resultados_estruturados if r.get('processamento_sucesso')])} ")
print(f"   Erros: {len(erros)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Converter para DataFrame e Salvar

# COMMAND ----------

# Criar DataFrame Pandas
df_resultados_pandas = pd.DataFrame(resultados_estruturados)

# Converter para Spark
df_resultados_spark = spark.createDataFrame(df_resultados_pandas)

# Adicionar metadados de processamento
df_resultados_spark = df_resultados_spark \
    .withColumn("job_execution_id", F.lit(f"PHI4_MAMOGRAFIA_{datetime.now().strftime('%Y%m%d_%H%M%S')}")) \
    .withColumn("dt_processamento", F.current_date()) \
    .withColumn("modalidade", F.lit("MAMOGRAFIA")) \
    .withColumn("modelo_llm", F.lit("phi4:14b"))

print("✅ DataFrame criado")
df_resultados_spark.printSchema()

# COMMAND ----------

# Salvar em Delta Lake
df_resultados_spark.write \
    .format("delta") \
    .mode("append") \
    .option("mergeSchema", "true") \
    .partitionBy("dt_processamento") \
    .saveAsTable(OUTPUT_TABLE)

print(f"✅ Dados salvos em: {OUTPUT_TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Análises de Qualidade

# COMMAND ----------

# Estatísticas gerais
df_stats = spark.sql(f"""
SELECT 
    COUNT(*) as total_laudos,
    SUM(CASE WHEN processamento_sucesso THEN 1 ELSE 0 END) as sucessos,
    SUM(CASE WHEN NOT processamento_sucesso THEN 1 ELSE 0 END) as erros,
    ROUND(AVG(confianca_media), 2) as confianca_media_geral,
    ROUND(MIN(confianca_minima), 2) as confianca_minima_geral,
    SUM(CASE WHEN tem_erros_validacao THEN 1 ELSE 0 END) as laudos_com_erros_validacao,
    SUM(num_anotacoes_llm) as total_anotacoes_llm
FROM {OUTPUT_TABLE}
WHERE dt_processamento = CURRENT_DATE
""")

print("📊 ESTATÍSTICAS GERAIS:")
display(df_stats)

# COMMAND ----------

# Distribuição BI-RADS
df_birads = spark.sql(f"""
SELECT 
    birads,
    COUNT(*) as quantidade,
    ROUND(AVG(confianca_media), 2) as confianca_media,
    ROUND(AVG(num_achados), 1) as media_achados
FROM {OUTPUT_TABLE}
WHERE dt_processamento = CURRENT_DATE
    AND processamento_sucesso = true
GROUP BY birads
ORDER BY birads
""")

print("📊 DISTRIBUIÇÃO BI-RADS:")
display(df_birads)

# COMMAND ----------

# Distribuição ACR (Densidade)
df_acr = spark.sql(f"""
SELECT 
    acr,
    COUNT(*) as quantidade,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentual
FROM {OUTPUT_TABLE}
WHERE dt_processamento = CURRENT_DATE
    AND processamento_sucesso = true
    AND acr IS NOT NULL
GROUP BY acr
ORDER BY acr
""")

print("📊 DISTRIBUIÇÃO ACR (DENSIDADE):")
display(df_acr)

# COMMAND ----------

# Laudos com achados
df_achados = spark.sql(f"""
SELECT 
    CASE 
        WHEN num_achados = 0 THEN 'Sem achados'
        WHEN num_achados = 1 THEN '1 achado'
        WHEN num_achados BETWEEN 2 AND 3 THEN '2-3 achados'
        ELSE '4+ achados'
    END as categoria_achados,
    COUNT(*) as quantidade,
    ROUND(AVG(confianca_media), 2) as confianca_media
FROM {OUTPUT_TABLE}
WHERE dt_processamento = CURRENT_DATE
    AND processamento_sucesso = true
GROUP BY categoria_achados
ORDER BY categoria_achados
""")

print("📊 DISTRIBUIÇÃO DE ACHADOS:")
display(df_achados)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Casos com Baixa Confiança

# COMMAND ----------

# Laudos com confiança < 0.7
df_baixa_confianca = spark.sql(f"""
SELECT 
    cd_atendimento,
    birads,
    num_achados,
    ROUND(confianca_media, 2) as confianca_media,
    num_anotacoes_llm,
    SUBSTR(texto_original, 1, 200) as preview_laudo
FROM {OUTPUT_TABLE}
WHERE dt_processamento = CURRENT_DATE
    AND processamento_sucesso = true
    AND confianca_media < 0.7
ORDER BY confianca_media
LIMIT 20
""")

print("⚠️ LAUDOS COM BAIXA CONFIANÇA (<0.7):")
display(df_baixa_confianca)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Amostra de Laudos Estruturados

# COMMAND ----------

# Selecionar amostra variada
amostra = spark.sql(f"""
WITH amostra_estratificada AS (
    SELECT 
        cd_atendimento,
        birads,
        acr,
        num_achados,
        confianca_media,
        laudo_estruturado,
        ROW_NUMBER() OVER (PARTITION BY birads ORDER BY RAND()) as rn
    FROM {OUTPUT_TABLE}
    WHERE dt_processamento = CURRENT_DATE
        AND processamento_sucesso = true
)
SELECT 
    cd_atendimento,
    birads,
    acr,
    num_achados,
    ROUND(confianca_media, 2) as confianca,
    laudo_estruturado
FROM amostra_estratificada
WHERE rn <= 2
ORDER BY birads
""").limit(10)

print("📋 AMOSTRA DE LAUDOS ESTRUTURADOS:")
display(amostra)

# COMMAND ----------

# Exibir um laudo estruturado completo formatado
laudo_exemplo = amostra.collect()[0]

print("=" * 80)
print(f"EXEMPLO DE LAUDO ESTRUTURADO - CD_ATENDIMENTO: {laudo_exemplo.cd_atendimento}")
print("=" * 80)
print(json.dumps(json.loads(laudo_exemplo.laudo_estruturado), indent=2, ensure_ascii=False))
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 11. Erros de Processamento

# COMMAND ----------

if len(erros) > 0:
    df_erros = spark.sql(f"""
    SELECT 
        cd_atendimento,
        erro_mensagem,
        SUBSTR(texto_original, 1, 200) as preview_laudo
    FROM {OUTPUT_TABLE}
    WHERE dt_processamento = CURRENT_DATE
        AND processamento_sucesso = false
    LIMIT 50
    """)
    
    print(f"❌ {len(erros)} ERROS ENCONTRADOS:")
    display(df_erros)
else:
    print("✅ Nenhum erro de processamento!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 12. Resumo Final

# COMMAND ----------

stats = df_resultados_spark.filter(F.col("processamento_sucesso") == True).agg(
    F.count("*").alias("total"),
    F.avg("confianca_media").alias("conf_media"),
    F.sum(F.when(F.col("birads") == "4", 1).otherwise(0)).alias("birads_4"),
    F.sum(F.when(F.col("birads") == "5", 1).otherwise(0)).alias("birads_5"),
    F.sum(F.when(F.col("num_achados") > 0, 1).otherwise(0)).alias("com_achados")
).collect()[0]

print("=" * 80)
print("RESUMO DA EXECUÇÃO - ESTRUTURAÇÃO CSV MAMOGRAFIA")
print("=" * 80)
print(f"📂 Arquivo CSV: {CSV_PATH}")
print(f"📊 Tabela destino: {OUTPUT_TABLE}")
print(f"🤖 Modelo: Phi-4 14B (via Ollama)")
print(f"")
print(f"📈 RESULTADOS:")
print(f"   Total processado: {len(resultados_estruturados)}")
print(f"   Sucessos: {stats['total']}")
print(f"   Erros: {len(erros)}")
print(f"   Taxa de sucesso: {stats['total'] / len(resultados_estruturados) * 100:.1f}%")
print(f"")
print(f"📊 QUALIDADE:")
print(f"   Confiança média: {stats['conf_media']:.2f}")
print(f"   BI-RADS 4: {stats['birads_4']}")
print(f"   BI-RADS 5: {stats['birads_5']}")
print(f"   Laudos com achados: {stats['com_achados']}")
print(f"")
print(f"⏱️  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
print("✅ Processamento concluído com sucesso!")
print("")
print("📌 PRÓXIMOS PASSOS:")
print("   1. Validar amostra com médicos radiologistas")
print("   2. Analisar casos de baixa confiança")
print("   3. Revisar laudos BI-RADS 4 e 5")
print("   4. Exportar para sistema de visualização")
print("=" * 80)

