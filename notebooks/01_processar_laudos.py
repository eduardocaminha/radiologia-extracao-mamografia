# Databricks notebook source
# MAGIC %md
# MAGIC # Estruturação de Laudos de Mamografia
# MAGIC 
# MAGIC Notebook para processar laudos de mamografia usando Phi-4

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Setup Inicial

# COMMAND ----------

# Instalar Ollama (executar uma vez)
# %sh
# curl -fsSL https://ollama.com/install.sh | sh
# nohup ollama serve > /tmp/ollama.log 2>&1 &
# sleep 5
# ollama pull phi4:14b

# COMMAND ----------

# Verificar se Ollama está rodando
import requests

try:
    response = requests.get("http://localhost:11434/api/tags")
    if response.status_code == 200:
        print("✅ Ollama está rodando")
        print("Modelos disponíveis:", [m["name"] for m in response.json()["models"]])
    else:
        print("❌ Ollama não está respondendo corretamente")
except Exception as e:
    print(f"❌ Erro ao conectar: {e}")
    print("Execute o setup do Ollama na célula anterior")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Importar Biblioteca

# COMMAND ----------

import sys
sys.path.append("/Workspace/Users/seu_usuario/estruturacao-mamografia")

from src.extractor import LaudoExtractor
from src.validators import validar_laudo_estruturado, calcular_metricas_confianca, extrair_anotacoes_llm
import json

# COMMAND ----------

# Inicializar extrator
extractor = LaudoExtractor(
    model="phi4:14b",
    template_path="/Workspace/Users/seu_usuario/estruturacao-mamografia/config/template.json",
    prompt_path="/Workspace/Users/seu_usuario/estruturacao-mamografia/config/prompt_extracao_mamografia.md"
)

print("✅ Extrator inicializado")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Teste com Laudo Individual

# COMMAND ----------

# Laudo de exemplo
laudo_exemplo = """
MAMOGRAFIA BILATERAL DIGITAL

DADOS CLÍNICOS: Rastreamento, paciente assintomática, 52 anos.

COMPARAÇÃO: Mamografia de 15/10/2023 disponível para comparação.

TÉCNICA: Mamografia digital (FFDM) bilateral nas incidências craniocaudal (CC) e médio-lateral oblíqua (MLO).

COMPOSIÇÃO MAMÁRIA: Mamas com padrão heterogeneamente denso (ACR C), o que pode obscurecer pequenas lesões.

ACHADOS:
- Mama direita: Nódulo irregular de margens espiculadas medindo 12mm no quadrante superior externo (QSE), 
  às 2 horas, distante 3,5cm do mamilo. Corresponde à nodulação palpável referida pela paciente.
  Achado novo em relação ao exame anterior.
- Mama esquerda: Sem alterações significativas.

IMPRESSÃO:
Nódulo irregular espiculado de 12mm em QSE da mama direita, BI-RADS 4.
Recomendada biópsia guiada por ultrassom.

Controle habitual da mama esquerda.

Dr. Rogério Silva - CRM 12345
"""

# Processar
resultado = extractor.processar(
    laudo_texto=laudo_exemplo,
    cd_atendimento="2024-10001"
)

# Mostrar resultado
print(json.dumps(resultado, indent=2, ensure_ascii=False))

# COMMAND ----------

# Validar resultado
erros = validar_laudo_estruturado(resultado, extractor.template)

if erros:
    print("⚠️ Erros de validação encontrados:")
    for erro in erros:
        print(f"  - {erro}")
else:
    print("✅ Laudo válido!")

# Métricas de confiança
metricas = calcular_metricas_confianca(resultado)
print(f"\n📊 Confiança média: {metricas['media']:.2f}")
print(f"   Mínima: {metricas['minima']:.2f}, Máxima: {metricas['maxima']:.2f}")

# Anotações do LLM
anotacoes = extrair_anotacoes_llm(resultado)
if anotacoes:
    print(f"\n📝 Anotações do LLM ({len(anotacoes)}):")
    for anotacao in anotacoes:
        print(f"  - {anotacao}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Processamento em Lote

# COMMAND ----------

# Ler laudos do Delta Lake
df_laudos = spark.table("seu_schema.laudos_mamografia_raw")

# Mostrar amostra
display(df_laudos.limit(5))

# COMMAND ----------

# Coletar laudos para processar (amostra pequena para teste)
laudos_sample = df_laudos.limit(10).collect()

laudos_list = [
    {
        "cd_atendimento": row.cd_atendimento,
        "texto": row.texto_laudo,
        "dt_exame": row.dt_exame
    }
    for row in laudos_sample
]

# Processar lote
resultados = extractor.processar_lote(
    laudos=laudos_list,
    campo_texto="texto",
    campo_cd="cd_atendimento",
    verbose=True
)

print(f"\n✅ Processados: {len(resultados)} laudos")
print(f"   Sucessos: {sum(1 for r in resultados if r.get('_sucesso'))}")
print(f"   Erros: {sum(1 for r in resultados if not r.get('_sucesso'))}")

# COMMAND ----------

# Converter para DataFrame
from pyspark.sql.types import StructType, StructField, StringType, FloatType, BooleanType
import pandas as pd

# Criar DataFrame Pandas primeiro
resultados_df = pd.DataFrame([
    {
        "cd_atendimento": r.get("cd_atendimento"),
        "sucesso": r.get("_sucesso", False),
        "erro": r.get("_erro"),
        "birads": r.get("categorias_diagnosticas_conclusao_laudo", {}).get("categoria_birads"),
        "acr": r.get("padrao_parenquimatoso", {}).get("classificacao_ACR"),
        "num_achados": len(r.get("descricao_achados", [])),
        "confianca_media": calcular_metricas_confianca(r)["media"] if r.get("_sucesso") else None,
        "json_completo": json.dumps(r, ensure_ascii=False)
    }
    for r in resultados
])

# Converter para Spark DataFrame
df_resultados = spark.createDataFrame(resultados_df)

display(df_resultados)

# COMMAND ----------

# Salvar resultados
df_resultados.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable("seu_schema.laudos_mamografia_estruturados")

print("✅ Resultados salvos em: seu_schema.laudos_mamografia_estruturados")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Análise de Qualidade

# COMMAND ----------

# Estatísticas de qualidade
stats = df_resultados.selectExpr(
    "count(*) as total",
    "sum(case when sucesso then 1 else 0 end) as sucessos",
    "avg(confianca_media) as confianca_media",
    "count(distinct birads) as num_birads_unicos"
).collect()[0]

print(f"""
📊 Estatísticas de Processamento:
   - Total processado: {stats.total}
   - Taxa de sucesso: {stats.sucessos / stats.total * 100:.1f}%
   - Confiança média: {stats.confianca_media:.2f}
   - BI-RADS únicos: {stats.num_birads_unicos}
""")

# COMMAND ----------

# Distribuição de BI-RADS
display(
    df_resultados
    .filter("sucesso = true")
    .groupBy("birads")
    .count()
    .orderBy("birads")
)

# COMMAND ----------

# Distribuição de ACR
display(
    df_resultados
    .filter("sucesso = true")
    .groupBy("acr")
    .count()
    .orderBy("acr")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. UDF para Processar na Tabela Inteira

# COMMAND ----------

from pyspark.sql.functions import udf, col
from pyspark.sql.types import StringType

# Criar UDF
@udf(returnType=StringType())
def estruturar_laudo_udf(texto, cd_atendimento):
    """UDF para processar laudos no Spark"""
    try:
        resultado = extractor.processar(texto, cd_atendimento=cd_atendimento)
        return json.dumps(resultado, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"erro": str(e), "_sucesso": False}, ensure_ascii=False)

# Aplicar na tabela inteira (cuidado com volume!)
df_todos = spark.table("seu_schema.laudos_mamografia_raw")

df_processado = df_todos.withColumn(
    "laudo_estruturado_json",
    estruturar_laudo_udf(col("texto_laudo"), col("cd_atendimento"))
)

# Salvar (pode demorar dependendo do volume)
# df_processado.write.format("delta").mode("overwrite").saveAsTable("seu_schema.laudos_processados_completo")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Casos de Erro - Análise

# COMMAND ----------

# Verificar casos com erro
df_erros = df_resultados.filter("sucesso = false")

if df_erros.count() > 0:
    print(f"⚠️ {df_erros.count()} laudos com erro")
    display(df_erros.select("cd_atendimento", "erro"))
else:
    print("✅ Nenhum erro encontrado!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Exportar Amostra para Validação Manual

# COMMAND ----------

# Selecionar amostra aleatória para validação manual
amostra_validacao = df_resultados \
    .filter("sucesso = true") \
    .sample(fraction=0.1, seed=42) \
    .limit(20)

# Exportar para CSV
amostra_validacao.toPandas().to_csv(
    "/dbfs/tmp/amostra_validacao_mamografia.csv",
    index=False
)

print("✅ Amostra exportada para: /dbfs/tmp/amostra_validacao_mamografia.csv")
print("   Use para validação manual com médicos radiologistas")

