# Databricks notebook source
# MAGIC %md
# MAGIC # Setup Ollama + Phi-4 (Databricks - Sem Sudo)
# MAGIC 
# MAGIC **Executar 1x por cluster** antes de processar laudos
# MAGIC 
# MAGIC Este notebook:
# MAGIC 1. Instala Ollama em diretório local (sem sudo)
# MAGIC 2. Inicia o serviço
# MAGIC 3. Baixa o modelo Phi-4 14B
# MAGIC 4. Valida instalação
# MAGIC 
# MAGIC **Tempo estimado:** ~15 minutos (download 8GB)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Verificar Arquitetura do Sistema

# COMMAND ----------

# MAGIC %sh
# MAGIC echo "🔍 Verificando arquitetura do sistema:"
# MAGIC uname -m
# MAGIC uname -a

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Baixar Ollama (Instalação Local)

# COMMAND ----------

# MAGIC %sh
# MAGIC # Detectar arquitetura
# MAGIC ARCH=$(uname -m)
# MAGIC echo "Arquitetura detectada: $ARCH"
# MAGIC 
# MAGIC # Criar diretório local
# MAGIC mkdir -p ~/.local/bin
# MAGIC cd ~/.local/bin
# MAGIC 
# MAGIC # Baixar binário correto para arquitetura
# MAGIC if [ "$ARCH" = "x86_64" ]; then
# MAGIC     echo "Baixando Ollama para x86_64 (AMD64)..."
# MAGIC     curl -L https://ollama.com/download/ollama-linux-amd64 -o ollama
# MAGIC elif [ "$ARCH" = "aarch64" ]; then
# MAGIC     echo "Baixando Ollama para ARM64..."
# MAGIC     curl -L https://ollama.com/download/ollama-linux-arm64 -o ollama
# MAGIC else
# MAGIC     echo "❌ Arquitetura não suportada: $ARCH"
# MAGIC     exit 1
# MAGIC fi
# MAGIC 
# MAGIC # Verificar download
# MAGIC echo ""
# MAGIC echo "Arquivo baixado:"
# MAGIC ls -lh ollama
# MAGIC file ollama
# MAGIC 
# MAGIC # Tornar executável
# MAGIC chmod +x ollama
# MAGIC 
# MAGIC # Verificar se é executável válido
# MAGIC if ./ollama --version 2>/dev/null; then
# MAGIC     echo "✅ Ollama instalado com sucesso!"
# MAGIC else
# MAGIC     echo "❌ Arquivo não é executável válido"
# MAGIC     echo "Tentando método alternativo..."
# MAGIC     
# MAGIC     # Método alternativo: usar script de instalação modificado
# MAGIC     rm -f ollama
# MAGIC     curl -fsSL https://ollama.com/install.sh | sed 's/sudo //g' | bash
# MAGIC fi

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Configurar PATH

# COMMAND ----------

import os
os.environ['PATH'] = f"{os.path.expanduser('~/.local/bin')}:{os.environ['PATH']}"

# Testar
import subprocess
result = subprocess.run(['which', 'ollama'], capture_output=True, text=True, env=os.environ)
if result.returncode == 0:
    print(f"✅ Ollama encontrado em: {result.stdout.strip()}")
    # Verificar versão
    version_result = subprocess.run(['ollama', '--version'], capture_output=True, text=True, env=os.environ)
    print(f"Versão: {version_result.stdout.strip()}")
else:
    print("❌ Ollama não encontrado no PATH")
    print("Execute a célula anterior novamente")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Iniciar Serviço Ollama

# COMMAND ----------

import subprocess
import time
import os

# Adicionar PATH
os.environ['PATH'] = f"{os.path.expanduser('~/.local/bin')}:{os.environ['PATH']}"

# Matar processos anteriores
subprocess.run(['pkill', '-f', 'ollama'], stderr=subprocess.DEVNULL)
time.sleep(2)

# Iniciar novo serviço
print("Iniciando Ollama...")
process = subprocess.Popen(
    [os.path.expanduser('~/.local/bin/ollama'), 'serve'],
    stdout=open('/tmp/ollama.log', 'w'),
    stderr=subprocess.STDOUT,
    env=os.environ
)

# Aguardar inicialização
time.sleep(10)

print(f"✅ Ollama iniciado (PID: {process.pid})")
print("Logs em: /tmp/ollama.log")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Testar Conexão

# COMMAND ----------

import requests
import time

# Aguardar serviço estar pronto
for i in range(10):
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print("✅ Ollama está respondendo!")
            break
    except:
        print(f"Tentativa {i+1}/10 - Aguardando Ollama iniciar...")
        time.sleep(3)
else:
    print("❌ Ollama não respondeu após 30 segundos")
    print("\n📋 Últimas linhas do log:")

# COMMAND ----------

# Ver últimas linhas do log
print("📋 LOG DO OLLAMA:")
print("=" * 80)

# COMMAND ----------

# MAGIC %sh
# MAGIC tail -30 /tmp/ollama.log

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Baixar Modelo Phi-4 14B
# MAGIC 
# MAGIC **Download: ~8GB, pode demorar 10-15 minutos**

# COMMAND ----------

import subprocess
import os

# Garantir PATH
os.environ['PATH'] = f"{os.path.expanduser('~/.local/bin')}:{os.environ['PATH']}"

print("Baixando Phi-4 14B (isso vai demorar ~10-15 min)...")
print("=" * 80)

result = subprocess.run(
    [os.path.expanduser('~/.local/bin/ollama'), 'pull', 'phi4:14b'],
    capture_output=True,
    text=True,
    env=os.environ
)

print(result.stdout)
if result.returncode == 0:
    print("=" * 80)
    print("✅ Phi-4 14B baixado com sucesso!")
else:
    print("=" * 80)
    print("❌ Erro ao baixar Phi-4:")
    print(result.stderr)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Listar Modelos Instalados

# COMMAND ----------

import subprocess
import os

os.environ['PATH'] = f"{os.path.expanduser('~/.local/bin')}:{os.environ['PATH']}"

result = subprocess.run(
    [os.path.expanduser('~/.local/bin/ollama'), 'list'],
    capture_output=True,
    text=True,
    env=os.environ
)

print("📦 MODELOS INSTALADOS:")
print("=" * 80)
print(result.stdout)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Testar Modelo Phi-4

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
        print(f"Tokens gerados: {result.get('eval_count', 'N/A')}")
    else:
        print(f"❌ Erro: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ Erro ao testar modelo: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Teste com JSON Estruturado

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
# MAGIC ## 10. Verificação Final

# COMMAND ----------

import requests
import os

print("=" * 80)
print("VERIFICAÇÃO FINAL - OLLAMA + PHI-4")
print("=" * 80)

# 1. Ollama instalado?
ollama_path = os.path.expanduser('~/.local/bin/ollama')
if os.path.exists(ollama_path):
    print(f"✅ Ollama: Instalado em {ollama_path}")
else:
    print("❌ Ollama: Binário não encontrado")

# 2. Serviço rodando?
try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    if response.status_code == 200:
        print("✅ Ollama: Serviço rodando")
        modelos = response.json()["models"]
        print(f"   Modelos instalados: {len(modelos)}")
        for m in modelos:
            size_gb = m.get('size', 0) / 1e9
            print(f"   - {m['name']} ({size_gb:.1f} GB)")
    else:
        print("❌ Ollama: Serviço não está respondendo")
except Exception as e:
    print(f"❌ Ollama: Não acessível - {e}")

# 3. Phi-4 disponível?
try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    modelos = [m["name"] for m in response.json()["models"]]
    if any("phi4" in m for m in modelos):
        print("✅ Phi-4: Instalado e disponível")
    else:
        print("❌ Phi-4: Não encontrado")
except:
    print("❌ Phi-4: Não foi possível verificar")

# 4. Geração funciona?
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
print("   Execute: notebooks/02_processar_csv_mamografia.py (produção)")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Troubleshooting

# COMMAND ----------

# MAGIC %md
# MAGIC ### Ver logs do Ollama

# COMMAND ----------

# MAGIC %sh
# MAGIC echo "📋 ÚLTIMAS 50 LINHAS DO LOG:"
# MAGIC echo "=========================================="
# MAGIC tail -50 /tmp/ollama.log

# COMMAND ----------

# MAGIC %md
# MAGIC ### Reiniciar Ollama (se necessário)

# COMMAND ----------

import subprocess
import time
import os

# Configurar PATH
os.environ['PATH'] = f"{os.path.expanduser('~/.local/bin')}:{os.environ['PATH']}"

# Matar processos
subprocess.run(['pkill', '-f', 'ollama'], stderr=subprocess.DEVNULL)
time.sleep(2)

# Reiniciar
process = subprocess.Popen(
    [os.path.expanduser('~/.local/bin/ollama'), 'serve'],
    stdout=open('/tmp/ollama.log', 'w'),
    stderr=subprocess.STDOUT,
    env=os.environ
)

time.sleep(10)
print(f"✅ Ollama reiniciado (PID: {process.pid})")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Redownload do modelo (se corrompido)

# COMMAND ----------

# import subprocess
# import os
# 
# os.environ['PATH'] = f"{os.path.expanduser('~/.local/bin')}:{os.environ['PATH']}"
# 
# # Remover modelo
# subprocess.run([os.path.expanduser('~/.local/bin/ollama'), 'rm', 'phi4:14b'], env=os.environ)
# 
# # Redownload
# subprocess.run([os.path.expanduser('~/.local/bin/ollama'), 'pull', 'phi4:14b'], env=os.environ)

# COMMAND ----------

# MAGIC %md
# MAGIC ## ⚠️ Importante: Persistência no Cluster
# MAGIC 
# MAGIC **Ollama é instalado em `/tmp/` e `~/.local/`** - esses diretórios podem ser limpos quando o cluster reinicia.
# MAGIC 
# MAGIC **Opções:**
# MAGIC 1. **Reexecutar este notebook** após restart do cluster (~2 min se Phi-4 já estiver em cache)
# MAGIC 2. **Usar Init Script** (configurar no cluster para instalar automaticamente)
# MAGIC 3. **Usar cluster de longa duração** (não desligar entre jobs)
# MAGIC 
# MAGIC Para criar Init Script, veja documentação em: notebooks/README.md
