# Estruturação de Laudos de Mamografia

Sistema de estruturação automática de laudos de mamografia usando LLM (Phi-4) seguindo padrão científico internacional.

[![GitHub](https://img.shields.io/badge/GitHub-radiologia--extracao--mamografia-blue)](https://github.com/eduardocaminha/radiologia-extracao-mamografia)

## 📋 Estrutura do Projeto

```
.
├── README.md                              # Este arquivo
├── requirements.txt                       # Dependências Python
├── config/
│   ├── template.json                      # Template de estruturação
│   └── prompt_extracao_mamografia.md      # Prompt do LLM
├── notebooks/
│   ├── README.md                          # Documentação dos notebooks
│   ├── 00_setup_ollama_phi4.py           # Setup Ollama + Phi-4 (1x por cluster)
│   ├── 01_processar_laudos.py            # Notebook teste/desenvolvimento
│   └── 02_processar_csv_mamografia.py    # Notebook produção (CSV → Delta)
├── src/
│   ├── __init__.py
│   ├── extractor.py                       # Classe principal
│   └── validators.py                      # Validação de outputs
└── tests/
    └── test_extracao.py                   # Testes unitários
```

## 🚀 Setup no Databricks

### 1. Clonar repositório

```python
# No Databricks Notebook
%sh
cd /Workspace/Users/seu_usuario/
git clone https://github.com/seu_usuario/estruturacao-mamografia.git
cd estruturacao-mamografia
```

### 2. Instalar Ollama + Phi-4

```bash
%sh
# Instalar Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Iniciar serviço (background)
nohup ollama serve > /tmp/ollama.log 2>&1 &

# Baixar Phi-4
ollama pull phi4:14b
```

### 3. Instalar dependências Python

```python
%pip install -r requirements.txt
```

### 4. Usar no notebook

```python
from src.extractor import LaudoExtractor

# Inicializar
extractor = LaudoExtractor(
    model="phi4:14b",
    template_path="config/template.json",
    prompt_path="config/prompt_extracao_mamografia.md"
)

# Processar laudo
laudo_texto = """
MAMOGRAFIA BILATERAL
Técnica: FFDM, incidências CC e MLO bilaterais
Composição: Mamas com padrão fibroglandular heterogêneo (ACR C)
Achados: Ausência de nódulos, calcificações suspeitas ou distorções arquiteturais
BI-RADS 1 - Negativo. Controle em 12 meses.
"""

resultado = extractor.processar(laudo_texto)
print(resultado)
```

## 📊 Processamento em Lote (Databricks)

### Opção 1: Processar CSV Direto (Recomendado)

Use o notebook `02_processar_csv_mamografia.py` para processar CSVs com colunas:
- `CD_ATENDIMENTO`, `DS_LAUDO_MEDICO`, `NM_PROCEDIMENTO`, etc.

```python
# Configurar no notebook
CSV_PATH = "/seu/caminho/para/laudos.csv"
OUTPUT_TABLE = "seu_catalog.seu_schema.mamografia_estruturada"
BATCH_SIZE = 100

# Executar notebook (Run All)
# Output: Delta Table com laudos estruturados + análises de qualidade
```

Ver documentação completa em: [`notebooks/README.md`](notebooks/README.md)

### Opção 2: Processar de Delta Lake Existente

```python
# Ler laudos do Delta Lake
df_laudos = spark.table("seu_schema.laudos_mamografia")

# UDF para processar
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType
import json

@udf(returnType=StringType())
def estruturar_laudo_udf(texto):
    try:
        resultado = extractor.processar(texto)
        return json.dumps(resultado, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"erro": str(e)})

# Aplicar
df_estruturado = df_laudos.withColumn(
    "laudo_estruturado",
    estruturar_laudo_udf("texto_laudo")
)

# Salvar
df_estruturado.write.format("delta").mode("overwrite").saveAsTable("seu_schema.laudos_estruturados")
```

## 🔧 Configuração

### Variáveis de Ambiente (opcional)

```python
import os
os.environ["OLLAMA_HOST"] = "http://localhost:11434"
os.environ["OLLAMA_MODEL"] = "phi4:14b"
```

## 📝 Template e Prompt

- **Template**: `config/template.json` - Estrutura JSON de saída
- **Prompt**: `config/prompt_extracao_mamografia.md` - Instruções para o LLM

## 🧪 Testes

```bash
%sh
cd /Workspace/Users/seu_usuario/estruturacao-mamografia
python -m pytest tests/ -v
```

## 📈 Performance Esperada

- **Precisão**: ~90-93% (Phi-4)
- **Velocidade**: ~2-3 laudos/segundo (GPU T4)
- **Taxa de erro**: <5%

## 🔍 Validação de Qualidade

O sistema inclui validação automática:
- ✅ JSON válido
- ✅ Campos obrigatórios presentes
- ✅ Valores dentro do domínio permitido
- ✅ Confiança do modelo (0.0-1.0)

## 📚 Referências

Template baseado em: "Preparation of a radiology department in an Italian Hospital dedicated to COVID-19 patients" - Radiol Med. 2020

## 🆘 Troubleshooting

### Ollama não inicia
```bash
%sh
ps aux | grep ollama
# Se não estiver rodando:
ollama serve &
```

### Modelo não encontrado
```bash
%sh
ollama list
# Se phi4 não aparecer:
ollama pull phi4:14b
```

### GPU não detectada
```python
import torch
print(torch.cuda.is_available())
# Se False, verificar cluster Databricks (precisa GPU runtime)
```

## 📧 Contato

Para dúvidas ou contribuições, abra uma issue no GitHub.

