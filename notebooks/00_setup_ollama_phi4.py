# Databricks notebook source
# MAGIC %md
# MAGIC # Setup Ollama + Phi-4
# MAGIC 
# MAGIC **Executar 1x por cluster** antes de processar laudos
# MAGIC 
# MAGIC Este notebook:
# MAGIC 1. Instala Ollama
# MAGIC 2. Inicia o serviço
# MAGIC 3. Baixa o modelo Phi-4 14B
# MAGIC 4. Valida instalação
# MAGIC 
# MAGIC **Tempo estimado:** ~15 minutos (download 8GB)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Instalar Ollama

# COMMAND ----------

# MAGIC %sh
# MAGIC curl -fsSL https://ollama.com/install.sh | sh

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Iniciar Serviço Ollama

# COMMAND ----------

# MAGIC %sh
# MAGIC # Matar processos anteriores se existirem
# MAGIC pkill ollama || true
# MAGIC 
# MAGIC # Iniciar novo serviço em background
# MAGIC nohup ollama serve > /tmp/ollama.log 2>&1 &
# MAGIC 
# MAGIC # Aguardar inicialização
# MAGIC sleep 10
# MAGIC 
# MAGIC # Verificar status
# MAGIC echo "Status do serviço:"
# MAGIC ps aux | grep ollama | grep -v grep || echo "Ollama não está rodando"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Testar Conexão

# COMMAND ----------

import requests
import time

# Aguardar serviço estar pronto
for i in range(10):
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print("✅ Ollama está rodando!")
            break
    except:
        print(f"Tentativa {i+1}/10 - Aguardando Ollama iniciar...")
        time.sleep(3)
else:
    print("❌ Ollama não respondeu após 30 segundos")
    print("Verifique logs: %sh cat /tmp/ollama.log")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Baixar Modelo Phi-4 14B
# MAGIC 
# MAGIC **Download: ~8GB, pode demorar 10-15 minutos**

# COMMAND ----------

# MAGIC %sh
# MAGIC ollama pull phi4:14b

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Listar Modelos Instalados

# COMMAND ----------

# MAGIC %sh
# MAGIC ollama list

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Testar Modelo Phi-4

# COMMAND ----------

import requests
import json

# Testar geração
payload = {
    "model": "phi4:14b",
    "prompt": "Responda apenas: OK",
    "stream": False,
    "options": {
        "temperature": 0.1,
        "num_predict": 10
    }
}

try:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json=payload,
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Phi-4 funcionando!")
        print(f"Resposta: {result['response']}")
    else:
        print(f"❌ Erro: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ Erro ao testar modelo: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Teste com JSON Estruturado

# COMMAND ----------

import requests
import json

# Testar geração de JSON
prompt = """Extraia o BI-RADS do laudo abaixo e retorne em JSON:

LAUDO: Mamografia bilateral normal. BI-RADS 1. Controle em 12 meses.

Retorne apenas:
{"birads": "1", "descricao": "normal"}
"""

payload = {
    "model": "phi4:14b",
    "prompt": prompt,
    "stream": False,
    "format": "json",
    "options": {
        "temperature": 0.1,
        "num_predict": 100
    }
}

try:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json=payload,
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        output = json.loads(result['response'])
        print("✅ Geração de JSON funcionando!")
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"❌ Erro: {response.status_code}")
        
except Exception as e:
    print(f"❌ Erro: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Verificação Final

# COMMAND ----------

import requests

print("=" * 80)
print("VERIFICAÇÃO FINAL - OLLAMA + PHI-4")
print("=" * 80)

# 1. Serviço rodando?
try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    if response.status_code == 200:
        print("✅ Ollama: Rodando")
        modelos = response.json()["models"]
        print(f"   Modelos instalados: {len(modelos)}")
        for m in modelos:
            print(f"   - {m['name']} ({m['size'] / 1e9:.1f} GB)")
    else:
        print("❌ Ollama: Erro de conexão")
except Exception as e:
    print(f"❌ Ollama: Não acessível - {e}")

# 2. Phi-4 disponível?
try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    modelos = [m["name"] for m in response.json()["models"]]
    if any("phi4" in m for m in modelos):
        print("✅ Phi-4: Instalado")
    else:
        print("❌ Phi-4: Não encontrado")
        print("   Execute: %sh ollama pull phi4:14b")
except:
    print("❌ Phi-4: Não foi possível verificar")

# 3. Geração funciona?
try:
    test_response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "phi4:14b", "prompt": "teste", "stream": False},
        timeout=30
    )
    if test_response.status_code == 200:
        print("✅ Geração: Funcionando")
    else:
        print("❌ Geração: Erro")
except Exception as e:
    print(f"❌ Geração: Falhou - {e}")

print("=" * 80)
print("\n📌 PRÓXIMO PASSO:")
print("   Execute: notebooks/01_processar_laudos.py (testes)")
print("   Ou: notebooks/02_processar_csv_mamografia.py (produção)")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Troubleshooting

# COMMAND ----------

# Ver logs do Ollama
print("📋 ÚLTIMAS 50 LINHAS DO LOG:")
print("=" * 80)

# COMMAND ----------

# MAGIC %sh
# MAGIC tail -50 /tmp/ollama.log

# COMMAND ----------

# Reiniciar Ollama se necessário
# COMANDO: Descomente e execute se precisar reiniciar

# %sh
# pkill ollama
# nohup ollama serve > /tmp/ollama.log 2>&1 &
# sleep 10

# COMMAND ----------

# Redownload do modelo se necessário
# COMANDO: Descomente se o modelo estiver corrompido

# %sh
# ollama rm phi4:14b
# ollama pull phi4:14b

