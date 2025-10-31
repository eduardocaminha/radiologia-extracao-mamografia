# Notebooks - Processamento de Laudos

## 📋 Notebooks Disponíveis

### 0. `00_setup_transformers_phi4.py` 🔧
**Executar 1x por cluster** antes de usar os outros notebooks.

Instala e configura:
- Transformers + Accelerate + BitsAndBytes
- Modelo Phi-3.5 Mini (quantizado 4-bit)
- Testes de validação

**Tempo:** ~20-30 minutos (download modelo)

**Funciona em:**
- ✅ CPU (ARM64 / x86_64) - lento mas funcional
- ✅ GPU (NVIDIA) - 10-20x mais rápido

### 1. `01_processar_laudos.py`
Notebook de teste e desenvolvimento para processar laudos individuais ou pequenos lotes.

**Pré-requisito:** Executar `00_setup_transformers_phi4.py` primeiro

**Uso:**
- Testar o sistema com laudos de exemplo
- Debug de erros de estruturação
- Validação de qualidade
- Ajuste de prompts

### 2. `02_processar_csv_mamografia.py` ⭐
Notebook de produção para processar CSVs completos de mamografias.

**Pré-requisito:** Executar `00_setup_transformers_phi4.py` primeiro

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

## 🚀 Como Usar no Databricks

### Passo a Passo

1. **Clonar repositório**
```bash
%sh
cd /Workspace/Repos/<seu_usuario>/
git clone https://github.com/eduardocaminha/radiologia-extracao-mamografia.git
```

2. **Setup modelo (1x por cluster)**
   - Executar: `00_setup_transformers_phi4.py`
   - Aguardar: ~20-30 minutos (download)

3. **Configurar `02_processar_csv_mamografia.py`**
```python
CSV_PATH = "/seu/caminho/para/laudos.csv"
OUTPUT_TABLE = "seu_catalog.seu_schema.mamografia_estruturada"
BATCH_SIZE = 10  # CPU: 5-10, GPU: 50-100
```

4. **Executar**
   - Run All (Ctrl + Shift + Enter)

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

### Erro: Modelo não carrega (RAM insuficiente)
```python
# No notebook 00_setup, trocar quantização:
model = AutoModelForCausalLM.from_pretrained(
    "microsoft/Phi-3.5-mini-instruct",
    load_in_8bit=True  # Mais leve que 4bit
)
```

### Erro: GPU não detectada
```python
import torch
print(torch.cuda.is_available())
# False = usando CPU (funciona mas é lento)
```

### Performance lenta
- **CPU:** Normal, espere ~2-5 laudos/min
- **Solução:** Pedir cluster com GPU ao time infra
- Ajustar `BATCH_SIZE` menor (5-10)

### Download travou
```python
# Adicionar timeout no notebook 00_setup:
os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '3600'
```

## 📈 Performance Esperada

| Cluster | Hardware | Laudos/min | Uso |
|---------|----------|-----------|-----|
| CPU ARM64 | 4 cores | ~2-5 | Dev/Teste |
| CPU x86 | 8 cores | ~5-10 | Dev/Teste |
| g5.xlarge | A10G GPU | ~30-50 | Produção |
| g4dn.xlarge | T4 GPU | ~20-30 | Produção |

**Exemplo:** 1.000 laudos
- **CPU:** ~3-8 horas
- **GPU:** ~20-50 minutos

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

