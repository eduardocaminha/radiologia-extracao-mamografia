#!/bin/bash

# Databricks Init Script - Instalar Ollama + Phi-4
# 
# USO:
# 1. Upload deste arquivo para DBFS: /dbfs/databricks/init_scripts/install_ollama.sh
# 2. Configurar no cluster: Cluster → Edit → Advanced Options → Init Scripts
#    Path: dbfs:/databricks/init_scripts/install_ollama.sh
# 3. Restart cluster
#
# Após configurar, Ollama + Phi-4 estarão disponíveis automaticamente em todos os workers

set -e

echo "=========================================="
echo "Installing Ollama (Init Script)"
echo "=========================================="

# Criar diretórios
mkdir -p /opt/ollama
mkdir -p /var/log/ollama

# Baixar Ollama
echo "Downloading Ollama binary..."
curl -L https://ollama.com/download/ollama-linux-amd64 -o /opt/ollama/ollama
chmod +x /opt/ollama/ollama

# Criar symlink
ln -sf /opt/ollama/ollama /usr/local/bin/ollama

# Iniciar serviço em background
echo "Starting Ollama service..."
nohup /opt/ollama/ollama serve > /var/log/ollama/service.log 2>&1 &

# Aguardar serviço iniciar
sleep 15

# Verificar se está rodando
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "✅ Ollama service is running"
else
    echo "❌ Ollama service failed to start"
    cat /var/log/ollama/service.log
    exit 1
fi

# Baixar Phi-4 (pode demorar)
echo "Downloading Phi-4 model (this may take 10-15 minutes)..."
/opt/ollama/ollama pull phi4:14b

# Verificar modelo
echo "Verifying model installation..."
/opt/ollama/ollama list

echo "=========================================="
echo "✅ Ollama + Phi-4 installation complete"
echo "=========================================="

