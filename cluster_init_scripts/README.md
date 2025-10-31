# Cluster Init Scripts

Scripts para configurar Ollama + Phi-4 automaticamente no cluster Databricks.

## 🔧 Opção 1: Notebook Manual (Recomendado para Testes)

**Usar:** `notebooks/00_setup_ollama_phi4.py`

**Quando usar:**
- Testes e desenvolvimento
- Primeiro uso
- Clusters temporários

**Vantagens:**
- ✅ Fácil de executar
- ✅ Não precisa configurar cluster
- ✅ Debug visual

**Desvantagens:**
- ❌ Precisa reexecutar após restart do cluster

## 🚀 Opção 2: Init Script (Recomendado para Produção)

**Usar:** `install_ollama.sh`

**Quando usar:**
- Produção
- Múltiplos jobs
- Cluster de longa duração

**Vantagens:**
- ✅ Instalação automática no startup do cluster
- ✅ Não precisa reexecutar
- ✅ Todos os workers já têm Ollama

**Desvantagens:**
- ❌ Startup do cluster fica ~15 min mais lento
- ❌ Requer configuração do cluster

---

## 📋 Como Configurar Init Script

### Passo 1: Upload para DBFS

**Via Databricks Notebook:**

```python
# COMMAND ----------
# Criar conteúdo do script
script_content = """#!/bin/bash
# [copiar conteúdo de install_ollama.sh aqui]
"""

# Salvar no DBFS
dbutils.fs.put(
    "/databricks/init_scripts/install_ollama.sh",
    script_content,
    overwrite=True
)

print("✅ Script salvo em: dbfs:/databricks/init_scripts/install_ollama.sh")
```

**Via CLI (alternativa):**

```bash
databricks fs cp install_ollama.sh dbfs:/databricks/init_scripts/install_ollama.sh
```

### Passo 2: Configurar no Cluster

1. **Databricks → Compute → [Seu Cluster]**
2. **Edit**
3. **Advanced Options → Init Scripts**
4. **Add:**
   - Type: `DBFS`
   - Path: `dbfs:/databricks/init_scripts/install_ollama.sh`
5. **Confirm**
6. **Restart Cluster**

### Passo 3: Aguardar Startup

O cluster vai demorar ~15-20 min a mais no primeiro startup (download Phi-4).

**Verificar logs:**
- Cluster → Event Log
- Buscar por "Init script" logs

### Passo 4: Validar

```python
# Testar se Ollama está disponível
import requests

response = requests.get("http://localhost:11434/api/tags")
if response.status_code == 200:
    print("✅ Ollama rodando!")
    print("Modelos:", [m["name"] for m in response.json()["models"]])
else:
    print("❌ Ollama não encontrado")
```

---

## 🔍 Troubleshooting

### Init Script falhou

**Ver logs:**
```python
# Logs do init script
display(dbutils.fs.head("dbfs:/databricks/init_scripts/install_ollama.sh.log"))

# Logs do Ollama
%sh
cat /var/log/ollama/service.log
```

### Cluster não inicia

Se o init script estiver travando o startup:

1. Remove init script do cluster
2. Restart cluster
3. Debug o script manualmente:

```python
%sh
bash /dbfs/databricks/init_scripts/install_ollama.sh
```

### Modelo não baixou

```python
%sh
# Verificar se Ollama está rodando
curl http://localhost:11434/api/tags

# Tentar baixar manualmente
/opt/ollama/ollama pull phi4:14b
```

---

## 📊 Comparação

| Aspecto | Notebook Manual | Init Script |
|---------|----------------|-------------|
| Setup inicial | 2 min | 20 min |
| Após restart | Reexecutar (~2 min) | Automático |
| Complexidade | Baixa | Média |
| Debug | Fácil | Logs no cluster |
| Produção | ❌ | ✅ |
| Desenvolvimento | ✅ | ❌ |

---

## 💡 Recomendação

1. **Começar com notebook manual** (`00_setup_ollama_phi4.py`)
2. Validar que tudo funciona
3. **Se for para produção**, migrar para init script
4. Testar init script em cluster de teste primeiro

---

## 🆘 Suporte

- Logs: `/var/log/ollama/service.log`
- Status: `curl http://localhost:11434/api/tags`
- Processos: `ps aux | grep ollama`
- Modelos: `/opt/ollama/ollama list`

