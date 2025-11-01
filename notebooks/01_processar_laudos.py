# Databricks notebook source
# MAGIC %md
# MAGIC # Processar Laudos de Mamografia - Teste/Desenvolvimento
# MAGIC 
# MAGIC **Notebook para testar estruturação de laudos individuais**
# MAGIC 
# MAGIC Este notebook usa **Databricks Foundation Models** (serving endpoints).
# MAGIC Não precisa de setup ou instalação - modelos já estão disponíveis no workspace.
# MAGIC 
# MAGIC **Modelo configurado:**
# MAGIC - `databricks-meta-llama-3-3-70b-instruct` ← **Padrão** (~0.8s/laudo, 70B parâmetros)
# MAGIC 
# MAGIC **Alternativas:**
# MAGIC - `databricks-meta-llama-3-1-8b-instruct` ← Mais rápido (~0.2s/laudo, menos preciso)
# MAGIC 
# MAGIC **Performance testada:**
# MAGIC - ✅ JSON válido 100%
# MAGIC - ✅ Llama 3.3 70B: 0.80s/laudo, maior precisão
# MAGIC - ✅ Extração precisa de BI-RADS, ACR, achados

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Configuração

# COMMAND ----------

# Configurações
ENDPOINT_NAME = "databricks-meta-llama-3-3-70b-instruct"  # Mais preciso (70B parâmetros)
TEMPERATURE = 0.1  # Baixa = mais determinístico
MAX_TOKENS = 4096  # Máximo para JSON estruturado

# Paths (ajustar se necessário)
TEMPLATE_PATH = "/Workspace/Innovation/t_eduardo.caminha/radiologia-extracao-mamografia/config/template.json"
PROMPT_PATH = "/Workspace/Innovation/t_eduardo.caminha/radiologia-extracao-mamografia/config/prompt_extracao_mamografia.md"

print("=" * 80)
print("CONFIGURAÇÃO")
print("=" * 80)
print(f"Endpoint: {ENDPOINT_NAME}")
print(f"Temperature: {TEMPERATURE}")
print(f"Max tokens: {MAX_TOKENS}")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Carregar Template e Prompt

# COMMAND ----------

import json

# Carregar template
with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
    template = json.load(f)

print("✅ Template carregado")
print(f"   Campos principais: {list(template.keys())[:5]}...")

# Carregar prompt
with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
    prompt_instructions = f.read()

print("✅ Prompt carregado")
print(f"   Tamanho: {len(prompt_instructions)} caracteres")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Criar Função de Estruturação

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
import json
import time

def estruturar_laudo(laudo_texto: str, endpoint: str = ENDPOINT_NAME, verbose: bool = True) -> dict:
    """
    Estrutura laudo de mamografia usando Databricks Foundation Model
    
    Args:
        laudo_texto: Texto do laudo médico
        endpoint: Nome do endpoint de serving
        verbose: Imprimir logs
        
    Returns:
        dict com laudo estruturado + metadados
    """
    w = WorkspaceClient()
    
    # Criar prompt completo
    prompt_completo = f"""{prompt_instructions}

---

LAUDO A SER ESTRUTURADO:

{laudo_texto}

---

Retorne APENAS o JSON estruturado (sem texto antes ou depois):
"""
    
    messages = [
        ChatMessage(
            role=ChatMessageRole.SYSTEM,
            content="Você é um assistente especializado em estruturação de laudos de mamografia. Retorne APENAS JSON válido seguindo o template fornecido, sem texto adicional."
        ),
        ChatMessage(
            role=ChatMessageRole.USER,
            content=prompt_completo
        )
    ]
    
    if verbose:
        print(f"Enviando para {endpoint}...")
    
    start_time = time.time()
    
    try:
        response = w.serving_endpoints.query(
            name=endpoint,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE
        )
        
        elapsed = time.time() - start_time
        response_text = response.choices[0].message.content
        
        if verbose:
            print(f"✅ Resposta recebida em {elapsed:.2f}s")
        
        # Extrair JSON
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx == -1 or end_idx <= start_idx:
            raise ValueError("JSON não encontrado na resposta")
        
        json_str = response_text[start_idx:end_idx]
        laudo_estruturado = json.loads(json_str)
        
        # Adicionar metadados
        return {
            "sucesso": True,
            "laudo_estruturado": laudo_estruturado,
            "tempo_processamento_s": elapsed,
            "modelo": endpoint,
            "tamanho_resposta": len(response_text),
            "erro": None
        }
        
    except json.JSONDecodeError as e:
        return {
            "sucesso": False,
            "laudo_estruturado": None,
            "tempo_processamento_s": time.time() - start_time,
            "modelo": endpoint,
            "erro": f"Erro ao parsear JSON: {e}",
            "resposta_bruta": response_text if 'response_text' in locals() else None
        }
    except Exception as e:
        return {
            "sucesso": False,
            "laudo_estruturado": None,
            "tempo_processamento_s": time.time() - start_time,
            "modelo": endpoint,
            "erro": f"{type(e).__name__}: {e}"
        }

print("✅ Função estruturar_laudo() criada")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Teste com Laudo Simples

# COMMAND ----------

laudo_teste_1 = """
MAMOGRAFIA BILATERAL

Técnica: Mamografia digital (FFDM), incidências craniocaudal (CC) e médio-lateral oblíqua (MLO) bilaterais.

Composição do parênquima mamário: Mamas com padrão fibroglandular disperso (ACR B).

Achados: Ausência de nódulos, calcificações suspeitas, distorções arquiteturais ou outras alterações.

Impressão diagnóstica: BI-RADS 1 - Negativo. 
Recomendação: Controle mamográfico em 12 meses.
"""

print("=" * 80)
print("TESTE 1: LAUDO NORMAL")
print("=" * 80)

resultado_1 = estruturar_laudo(laudo_teste_1)

if resultado_1["sucesso"]:
    print("\n✅ SUCESSO!")
    print(f"   Tempo: {resultado_1['tempo_processamento_s']:.2f}s")
    print(f"\n📋 LAUDO ESTRUTURADO:")
    print(json.dumps(resultado_1["laudo_estruturado"], indent=2, ensure_ascii=False))
else:
    print(f"\n❌ ERRO: {resultado_1['erro']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Teste com Laudo Complexo (BI-RADS 4)

# COMMAND ----------

laudo_teste_2 = """
MAMOGRAFIA BILATERAL - DIAGNÓSTICA

INDICAÇÃO: Nódulo palpável em mama direita.

TÉCNICA: Mamografia digital de campo total (FFDM), incidências CC e MLO bilaterais, 
com incidências adicionais localizadas com compressão da mama direita.

COMPARAÇÃO: Mamografia de 15/10/2023 disponível.

COMPOSIÇÃO: Mamas heterogeneamente densas (ACR C), o que pode obscurecer pequenas massas.

ACHADOS:
Mama direita: Observa-se nódulo irregular de aproximadamente 15mm de diâmetro, com margens 
espiculadas e alta densidade, localizado no quadrante superior externo (QSE), às 2 horas, 
35mm do mamilo, profundidade média. Corresponde ao achado palpável. Novo em relação ao 
exame anterior.

Mama esquerda: Sem alterações significativas comparado ao exame prévio.

Linfonodos axilares: Não há linfonodomegalias axilares suspeitas bilateralmente.

IMPRESSÃO:
BI-RADS 4 - Achado suspeito na mama direita.

CONDUTA:
Biópsia percutânea guiada por ultrassom é recomendada para caracterização histológica 
do nódulo em QSE da mama direita.
"""

print("=" * 80)
print("TESTE 2: LAUDO COMPLEXO (BI-RADS 4)")
print("=" * 80)

resultado_2 = estruturar_laudo(laudo_teste_2)

if resultado_2["sucesso"]:
    print("\n✅ SUCESSO!")
    print(f"   Tempo: {resultado_2['tempo_processamento_s']:.2f}s")
    
    laudo = resultado_2["laudo_estruturado"]
    
    print(f"\n📊 RESUMO:")
    print(f"   BI-RADS: {laudo.get('categorias_diagnosticas_conclusao_laudo', {}).get('categoria_birads')}")
    print(f"   ACR: {laudo.get('padrao_parenquimatoso', {}).get('classificacao_ACR')}")
    print(f"   Achados: {len(laudo.get('descricao_achados', []))}")
    
    print(f"\n📋 JSON COMPLETO:")
    print(json.dumps(laudo, indent=2, ensure_ascii=False))
else:
    print(f"\n❌ ERRO: {resultado_2['erro']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Extrair Campos Chave

# COMMAND ----------

def extrair_campos_chave(laudo_estruturado: dict) -> dict:
    """
    Extrai campos principais do laudo estruturado para análise rápida
    """
    try:
        return {
            "cd_atendimento": laudo_estruturado.get("cd_atendimento"),
            "birads": laudo_estruturado.get("categorias_diagnosticas_conclusao_laudo", {}).get("categoria_birads"),
            "acr": laudo_estruturado.get("padrao_parenquimatoso", {}).get("classificacao_ACR"),
            "num_achados": len(laudo_estruturado.get("descricao_achados", [])),
            "setting": laudo_estruturado.get("setting", {}).get("tipo"),
            "lateralidade": laudo_estruturado.get("tecnica", {}).get("lateralidade"),
            "comparacao_disponivel": laudo_estruturado.get("comparacao_exames_previos", {}).get("disponivel"),
            "confianca_media": calcular_confianca_media(laudo_estruturado)
        }
    except Exception as e:
        return {"erro": str(e)}

def calcular_confianca_media(laudo: dict) -> float:
    """
    Calcula confiança média de todas as seções
    """
    confiancas = []
    
    # Percorrer todas as seções que têm 'confianca'
    for key, value in laudo.items():
        if isinstance(value, dict) and 'confianca' in value:
            conf = value['confianca']
            if isinstance(conf, (int, float)):
                confiancas.append(conf)
    
    return sum(confiancas) / len(confiancas) if confiancas else 0.0

# Testar extração
if resultado_2["sucesso"]:
    campos_chave = extrair_campos_chave(resultado_2["laudo_estruturado"])
    
    print("=" * 80)
    print("CAMPOS CHAVE EXTRAÍDOS")
    print("=" * 80)
    for campo, valor in campos_chave.items():
        print(f"{campo}: {valor}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Processar Lote de Laudos

# COMMAND ----------

# Exemplo: processar múltiplos laudos
laudos_teste = [
    ("LAUDO_001", laudo_teste_1),
    ("LAUDO_002", laudo_teste_2),
]

print("=" * 80)
print(f"PROCESSANDO LOTE DE {len(laudos_teste)} LAUDOS")
print("=" * 80)

resultados = []

for cd_atendimento, texto_laudo in laudos_teste:
    print(f"\nProcessando {cd_atendimento}...")
    
    resultado = estruturar_laudo(texto_laudo, verbose=False)
    
    if resultado["sucesso"]:
        # Adicionar CD_ATENDIMENTO ao laudo estruturado
        resultado["laudo_estruturado"]["cd_atendimento"] = cd_atendimento
        
        campos = extrair_campos_chave(resultado["laudo_estruturado"])
        print(f"  ✅ BI-RADS: {campos.get('birads')} | ACR: {campos.get('acr')} | {resultado['tempo_processamento_s']:.2f}s")
        
        resultados.append({
            "cd_atendimento": cd_atendimento,
            "sucesso": True,
            "laudo_estruturado": resultado["laudo_estruturado"],
            "tempo_s": resultado["tempo_processamento_s"]
        })
    else:
        print(f"  ❌ Erro: {resultado['erro']}")
        resultados.append({
            "cd_atendimento": cd_atendimento,
            "sucesso": False,
            "erro": resultado["erro"]
        })

print("\n" + "=" * 80)
print(f"✅ {len([r for r in resultados if r['sucesso']])} sucessos / {len(resultados)} total")
print(f"⏱️  Tempo médio: {sum([r.get('tempo_s', 0) for r in resultados if r['sucesso']]) / len([r for r in resultados if r['sucesso']]):.2f}s")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Análise de Qualidade

# COMMAND ----------

import pandas as pd

# Criar DataFrame com resultados
if resultados:
    df_resultados = pd.DataFrame([
        {
            "cd_atendimento": r["cd_atendimento"],
            "sucesso": r["sucesso"],
            "birads": r["laudo_estruturado"].get("categorias_diagnosticas_conclusao_laudo", {}).get("categoria_birads") if r["sucesso"] else None,
            "acr": r["laudo_estruturado"].get("padrao_parenquimatoso", {}).get("classificacao_ACR") if r["sucesso"] else None,
            "num_achados": len(r["laudo_estruturado"].get("descricao_achados", [])) if r["sucesso"] else None,
            "tempo_s": r.get("tempo_s")
        }
        for r in resultados
    ])
    
    display(df_resultados)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Exportar Resultados (Opcional)

# COMMAND ----------

# Salvar resultados em JSON
output_path = "/dbfs/tmp/laudos_processados_teste.json"

with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(resultados, f, ensure_ascii=False, indent=2)

print(f"✅ Resultados salvos em: {output_path}")
print(f"   Total: {len(resultados)} laudos")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📊 Próximos Passos
# MAGIC 
# MAGIC Para processar CSVs completos em produção:
# MAGIC → Use o notebook **`02_processar_csv_mamografia.py`**
# MAGIC 
# MAGIC Performance esperada:
# MAGIC - Llama 3.1 8B: ~5-6 laudos/segundo
# MAGIC - Llama 3.3 70B: ~1-2 laudos/segundo (mais preciso)

