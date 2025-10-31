# Databricks notebook source
# MAGIC %md
# MAGIC # Setup Phi-4 via Transformers (CPU ARM64)
# MAGIC 
# MAGIC **Para clusters SEM GPU e/ou ARM64**
# MAGIC 
# MAGIC Este notebook:
# MAGIC 1. Instala dependências (transformers, bitsandbytes)
# MAGIC 2. Baixa Phi-4 quantizado (4-bit para economizar RAM)
# MAGIC 3. Valida geração de JSON
# MAGIC 
# MAGIC **Tempo estimado:** ~20-30 minutos (download modelo)
# MAGIC 
# MAGIC **Requisitos:**
# MAGIC - RAM: mínimo 8GB (recomendado 16GB)
# MAGIC - CPU: qualquer arquitetura (x86_64 ou ARM64)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Verificar Recursos do Cluster

# COMMAND ----------

import platform
import psutil
import torch

print("=" * 80)
print("RECURSOS DO CLUSTER")
print("=" * 80)
print(f"Arquitetura: {platform.machine()}")
print(f"Python: {platform.python_version()}")
print(f"PyTorch: {torch.__version__}")
print(f"CUDA disponível: {torch.cuda.is_available()}")
print(f"")
print(f"CPU cores: {psutil.cpu_count()}")
print(f"RAM total: {psutil.virtual_memory().total / 1e9:.1f} GB")
print(f"RAM disponível: {psutil.virtual_memory().available / 1e9:.1f} GB")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Instalar Dependências

# COMMAND ----------

# MAGIC %pip install -q transformers>=4.40.0 accelerate>=0.25.0 bitsandbytes>=0.41.0 sentencepiece protobuf

# COMMAND ----------

# Restart Python (necessário após install)
dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Configurar Cache

# COMMAND ----------

import os
from pathlib import Path

# Criar diretório de cache local
cache_dir = "/tmp/huggingface_cache"
Path(cache_dir).mkdir(parents=True, exist_ok=True)

# Configurar variáveis de ambiente
os.environ['HF_HOME'] = cache_dir
os.environ['TRANSFORMERS_CACHE'] = cache_dir

print(f"✅ Cache configurado em: {cache_dir}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Baixar Phi-4 (Quantizado)
# MAGIC 
# MAGIC **Baixando modelo quantizado (4-bit) para economizar RAM**
# MAGIC 
# MAGIC - Modelo original: ~28GB
# MAGIC - Modelo 4-bit: ~8GB
# MAGIC 
# MAGIC ⏳ **Isso vai demorar 15-20 minutos**

# COMMAND ----------

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

print("Baixando Phi-4 Mini (otimizado para CPU)...")
print("=" * 80)

# Usar Phi-3.5 Mini ao invés de Phi-4 (menor e mais rápido em CPU)
model_name = "microsoft/Phi-3.5-mini-instruct"

try:
    # Baixar tokenizer
    print("1/2 Baixando tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        cache_dir=cache_dir,
        trust_remote_code=True
    )
    print("✅ Tokenizer baixado")
    
    # Baixar modelo quantizado
    print("\n2/2 Baixando modelo (4-bit quantizado)...")
    print("⏳ Aguarde ~15-20 minutos...")
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        cache_dir=cache_dir,
        trust_remote_code=True,
        torch_dtype=torch.float16,
        device_map="cpu",  # Forçar CPU
        low_cpu_mem_usage=True,
        load_in_4bit=True  # Quantização 4-bit
    )
    
    print("=" * 80)
    print("✅ Phi-3.5 Mini baixado com sucesso!")
    print(f"Parâmetros do modelo: ~3.8B")
    print(f"Memória estimada: ~2-3GB")
    
except Exception as e:
    print(f"❌ Erro ao baixar modelo: {e}")
    print("\n💡 Tentando abordagem alternativa (sem quantização)...")
    
    # Fallback: modelo sem quantização
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        cache_dir=cache_dir,
        trust_remote_code=True,
        torch_dtype=torch.float32,
        device_map="cpu",
        low_cpu_mem_usage=True
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Testar Geração Simples

# COMMAND ----------

import torch

# Prompt de teste
prompt = "Responda apenas: OK"

# Tokenizar
inputs = tokenizer(prompt, return_tensors="pt")

# Gerar resposta
print("Gerando resposta...")
with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=10,
        temperature=0.1,
        do_sample=True
    )

# Decodificar
response = tokenizer.decode(outputs[0], skip_special_tokens=True)

print("=" * 80)
print("TESTE DE GERAÇÃO")
print("=" * 80)
print(f"Prompt: {prompt}")
print(f"Resposta: {response}")
print("=" * 80)

if "OK" in response.upper():
    print("✅ Modelo funcionando!")
else:
    print("⚠️  Modelo gerou resposta, mas não exatamente 'OK'")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Teste com Extração de JSON

# COMMAND ----------

import json

# Prompt de teste com JSON
prompt = """Extraia o BI-RADS do laudo e retorne apenas JSON válido:

LAUDO: Mamografia bilateral normal. BI-RADS 1. Controle em 12 meses.

JSON (apenas o JSON, sem texto adicional):
"""

# Tokenizar
inputs = tokenizer(prompt, return_tensors="pt")

# Gerar
print("Gerando JSON...")
with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=100,
        temperature=0.1,
        do_sample=True
    )

response = tokenizer.decode(outputs[0], skip_special_tokens=True)

print("=" * 80)
print("TESTE DE EXTRAÇÃO JSON")
print("=" * 80)
print("Resposta completa:")
print(response)
print("=" * 80)

# Tentar extrair JSON da resposta
try:
    # Procurar por JSON na resposta
    start = response.find('{')
    end = response.rfind('}') + 1
    if start != -1 and end > start:
        json_str = response[start:end]
        parsed = json.loads(json_str)
        print("✅ JSON extraído com sucesso:")
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
    else:
        print("⚠️  JSON não encontrado na resposta")
except Exception as e:
    print(f"⚠️  Erro ao parsear JSON: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Criar Função Helper

# COMMAND ----------

def gerar_json_estruturado(prompt: str, max_tokens: int = 4096) -> str:
    """
    Gera JSON estruturado a partir de prompt
    
    Args:
        prompt: Prompt com instruções
        max_tokens: Máximo de tokens na resposta
        
    Returns:
        String com JSON gerado
    """
    # Tokenizar
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
    
    # Gerar
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.1,
            do_sample=True,
            top_p=0.95,
            repetition_penalty=1.1
        )
    
    # Decodificar
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Remover prompt da resposta
    response = response.replace(prompt, "").strip()
    
    return response

# Testar
test_result = gerar_json_estruturado("Retorne JSON: {\"teste\": \"ok\"}")
print("Teste da função:")
print(test_result[:200])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Salvar Modelo no DBFS (Opcional)
# MAGIC 
# MAGIC Para não precisar baixar novamente

# COMMAND ----------

# DESCOMENTE para salvar no DBFS
# 
# save_path = "/dbfs/models/phi35-mini-4bit"
# 
# print(f"Salvando modelo em: {save_path}")
# model.save_pretrained(save_path)
# tokenizer.save_pretrained(save_path)
# print("✅ Modelo salvo!")
# 
# # Para carregar depois:
# # model = AutoModelForCausalLM.from_pretrained(save_path, trust_remote_code=True)
# # tokenizer = AutoTokenizer.from_pretrained(save_path, trust_remote_code=True)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Verificação Final

# COMMAND ----------

import psutil

print("=" * 80)
print("VERIFICAÇÃO FINAL")
print("=" * 80)

# Modelo carregado?
try:
    print(f"✅ Modelo: {model_name}")
    print(f"   Device: {model.device}")
    print(f"   Dtype: {model.dtype}")
except:
    print("❌ Modelo não carregado")

# Tokenizer ok?
try:
    test = tokenizer("teste")
    print("✅ Tokenizer: Funcionando")
except:
    print("❌ Tokenizer: Erro")

# RAM disponível
mem = psutil.virtual_memory()
print(f"📊 RAM disponível: {mem.available / 1e9:.1f} GB / {mem.total / 1e9:.1f} GB")

# Teste rápido
try:
    inputs = tokenizer("teste", return_tensors="pt")
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=5)
    print("✅ Geração: Funcionando")
except Exception as e:
    print(f"❌ Geração: Erro - {e}")

print("=" * 80)
print("\n📌 PRÓXIMO PASSO:")
print("   Execute: notebooks/02_processar_csv_mamografia.py")
print("   (Versão adaptada para transformers)")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## ⚠️ Limitações CPU
# MAGIC 
# MAGIC **Phi-3.5 Mini em CPU:**
# MAGIC - Velocidade: ~2-5 laudos/minuto (10-30x mais lento que GPU)
# MAGIC - RAM: ~3-4GB por worker
# MAGIC - Funciona, mas é LENTO
# MAGIC 
# MAGIC **Alternativas mais rápidas:**
# MAGIC 1. Usar cluster com GPU (g5.xlarge) → ~30-40 laudos/min
# MAGIC 2. Usar API externa (Claude/GPT) → ~10-20 laudos/min
# MAGIC 3. Processar em lotes pequenos e deixar rodando overnight
# MAGIC 
# MAGIC **Para produção:** Recomendo solicitar cluster com GPU ao time de infra.

