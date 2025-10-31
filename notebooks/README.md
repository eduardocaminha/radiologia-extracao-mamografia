# Notebooks - Processamento de Laudos

## 📋 Notebooks Disponíveis

### 1. `01_processar_laudos.py`
Notebook de teste e desenvolvimento para processar laudos individuais ou pequenos lotes.

**Uso:**
- Testar o sistema com laudos de exemplo
- Debug de erros de estruturação
- Validação de qualidade
- Ajuste de prompts

### 2. `02_processar_csv_mamografia.py` ⭐
Notebook de produção para processar CSVs completos de mamografias.

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

## 🚀 Como Usar `02_processar_csv_mamografia.py`

### Pré-requisitos

1. **Ollama + Phi-4 rodando:**
```bash
# No Databricks cluster
%sh
curl -fsSL https://ollama.com/install.sh | sh
nohup ollama serve > /tmp/ollama.log 2>&1 &
ollama pull phi4:14b
```

2. **Projeto clonado no Workspace:**
```bash
%sh
cd /Workspace/Users/seu_usuario/
git clone https://github.com/eduardocaminha/radiologia-extracao-mamografia.git
```

### Passo a Passo

1. **Abrir notebook no Databricks**
   - Workspace → Import → `02_processar_csv_mamografia.py`

2. **Configurar parâmetros** (Seção 2):
```python
CSV_PATH = "/seu/caminho/para/laudos.csv"
OUTPUT_TABLE = "seu_catalog.seu_schema.mamografia_estruturada"
BATCH_SIZE = 100
```

3. **Atualizar paths** (Seção 1 e 3):
```python
sys.path.append("/Workspace/Users/SEU_USUARIO/radiologia-extracao-mamografia")

extractor = LaudoExtractor(
    template_path="/Workspace/Users/SEU_USUARIO/radiologia-extracao-mamografia/config/template.json",
    prompt_path="/Workspace/Users/SEU_USUARIO/radiologia-extracao-mamografia/config/prompt_extracao_mamografia.md"
)
```

4. **Executar todas as células**
   - Run All (Shift + Ctrl + Enter)

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

### Erro: "Ollama não disponível"
```bash
# Verificar se está rodando
%sh
curl http://localhost:11434/api/tags

# Se não estiver, iniciar
%sh
nohup ollama serve > /tmp/ollama.log 2>&1 &
sleep 5
ollama list
```

### Erro: "Modelo phi4:14b não encontrado"
```bash
%sh
ollama pull phi4:14b
ollama list
```

### Erro: Memória insuficiente
Ajustar `BATCH_SIZE` para valor menor:
```python
BATCH_SIZE = 50  # ou 25 para clusters menores
```

### Performance lenta
- Usar cluster com GPU (g5.xlarge ou maior)
- Aumentar `BATCH_SIZE` se tiver memória disponível
- Considerar processar subset primeiro para validar

## 📈 Performance Esperada

| Cluster | GPU | Laudos/min | Custo estimado |
|---------|-----|-----------|----------------|
| CPU only | - | ~5-10 | Baixo |
| g5.xlarge | A10G | ~30-40 | Médio |
| g5.2xlarge | A10G | ~50-60 | Alto |

**Exemplo:** 10.000 laudos
- g5.xlarge: ~4-5 horas
- Custo: ~$10-15 (DBU + compute)

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

