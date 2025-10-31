# Prompt: Estruturação de Laudos de Mamografia

## OBJETIVO

Você vai receber um laudo de mamografia em texto livre e deve estruturá-lo COMPLETAMENTE seguindo o template JSON fornecido.

**IMPORTANTE:** O template segue o padrão de estruturação de laudos mamográficos publicado em literatura científica. TODO laudo deve ser estruturado COMPLETO, independente de ter ou não achados patológicos.

## REGRAS OBRIGATÓRIAS

### 1. OUTPUT
- Retorne APENAS o JSON estruturado
- Sem texto antes ou depois do JSON
- Sem explicações adicionais
- Sem comentários no JSON
- JSON válido e bem formatado

### 2. TEMPLATE É LEI
- Use EXATAMENTE o template fornecido
- NUNCA invente novos campos
- NUNCA crie novas categorias ou valores
- Use APENAS os valores permitidos no template

**Como interpretar o template:**
- `"campo": "valor1|valor2|valor3"` → escolha UM dos valores separados por `|`
- `"campo": "tipo|null"` → valor do tipo especificado OU null
- `"campo": "boolean"` → true ou false
- `"campo": "float[0.0-1.0]"` → número decimal entre 0.0 e 1.0
- `"campo": "int[1-12]"` → número inteiro no range especificado
- `"campo": []` → array vazio por padrão
- `["enum: valor1|valor2"]` → array podendo conter zero ou mais valores da lista

**Campos de texto livre permitidos:**
- `cd_atendimento`, `patologias`, `localizacao` (especificar), `quem`, `outro`, `especificar`, `correspondencia_achado_clinico`, `texto` (conclusão), `confirmacao_histopatologica`
- IMPORTANTE: mesmo nesses campos, seja conciso e use terminologia médica do laudo original

### 3. MAPEAMENTO DE TEXTO LIVRE → VALORES FIXOS
Os laudos terão textos variados. Você DEVE mapear para os valores fixos do template.

**Exemplos:**
- "nódulo de contornos irregulares" → `forma: "irregular"`
- "margens mal definidas" → `margens: "indistinta_mal_definida"`
- "densidade heterogênea" → classificação ACR mais provável
- "calcificações grosseiras" → `morfologia_descricao: "grosseira_pipoca"`

### 4. NUNCA INVENTE INFORMAÇÃO
- Se a informação NÃO está no laudo, use `null` ou omita o campo
- Se não tem certeza, use `null` e explique em `anotacoes_llm`
- Não presuma informações que não estão explícitas
- Não complete dados faltantes

### 5. DÚVIDAS E INCERTEZAS
Use `anotacoes_llm` e `confianca` para expressar incerteza:

**`anotacoes_llm`**: array de strings explicando dúvidas (padrão: array vazio `[]`)
```json
"anotacoes_llm": [
  "Laudo menciona 'margens pouco nítidas' - mapeado como indistinta_mal_definida",
  "Categoria BI-RADS não explícita - inferida pelos achados descritos"
]
```

**Se não houver dúvidas:**
```json
"anotacoes_llm": []
```

**`confianca`**: float 0.0-1.0
- `1.0` = informação explícita e clara
- `0.8-0.9` = informação clara mas necessitou mapeamento de sinônimos
- `0.6-0.7` = informação ambígua ou incompleta
- `0.4-0.5` = inferência necessária
- `<0.4` = alta incerteza

---

## ESTRUTURA DO TEMPLATE

O template segue a estrutura padrão de laudos de mamografia:
1. Identificação e dados pessoais
2. Contexto do exame (setting)
3. Comparação com prévios
4. Anamnese e história clínica
5. Técnica utilizada
6. Composição do parênquima (sempre presente)
7. Descrição de achados (se houver)
8. Categoria BI-RADS
9. Conclusão

### cd_atendimento
- Código do atendimento (string)

### dados_pessoais
**Campos:** `peso`, `altura`, `imc`, `circunferencia_cintura` (float|null), `patologias` (string|null)

Preencha se mencionado explicitamente no laudo.

### setting
**tipo:**
- `avaliacao_rastreamento_organizado` = rastreamento em programa organizado
- `mamografia_diagnostica_rastreamento_oportunistico_mulher_assintomatica` = rastreamento individual, sem sintomas
- `mamografia_diagnostica_mulher_sintomatica` = investigação de sintoma/queixa
- `outro` = situações não cobertas acima

Se `outro`, preencha `outro_especificar`.

### comparacao_exames_previos
- `disponivel`: true se laudo menciona comparação com anterior
- `exame_data`: data do exame comparado (string|null)
- `imagens_disponiveis`: true se menciona visualização de imagens prévias
- `laudos_disponiveis`: true se menciona apenas laudos prévios

### anamnese_contexto_clinico

#### anamnese → historia_familiar_clinica_geral
- `terapia_reposicao_hormonal`: true se paciente usa TRH
- `sobrevivente_linfoma_radioterapia_toracica`: true se teve
- `historia_familiar_cancer_mama`: presente=true se familiar teve, especificar `quem` e `idade`
- `mutacoes_geneticas`: marcar true apenas genes mencionados
- `avaliacao_risco_cancer_mama_opcional`: texto livre se mencionado

#### anamnese → historia_clinica_mama
Marcar `realizada: true` apenas se mencionado:
- `biopsia_percutanea_previa`
- `cirurgia_previa_lesoes_benignas`
- `mastoplastia_aditiva_previa`
- `mastoplastia_redutora_previa`

Incluir `localizacao` se especificada.

#### questao_diagnostica
Array com sintomas/queixas mencionados (valores permitidos):
- `paciente_assintomatica`
- `nodulo_mama`
- `nodulo_axilar`
- `secrecao_papilar`
- `alteracoes_pele_mamilo`
- `mastodinia`
- `sintomas_inflamacao`
- `outro`

**Exemplos:**
- Rastreamento: `["paciente_assintomatica"]`
- Sintomática: `["nodulo_mama", "mastodinia"]`
- Sem informação: `[]`

### tecnica
- `lateralidade`: `bilateral` | `unilateral_direita` | `unilateral_esquerda`
- `tipo_mamografia`: 
  - `filme_ecran` = mamografia convencional
  - `mamografia_digital_CR` = computed radiography
  - `mamografia_digital_FFDM` = full field digital mammography
  - `tomossintese` = tomossíntese/3D
  - `outro`
- `dose_radiacao_mGy`: float se mencionado (extrair de DICOM ou texto)

### padrao_parenquimatoso
- `classificacao_ACR`: `A` | `B` | `C` | `D`
  - **A** = mamas predominantemente gordurosas
  - **B** = densidades fibroglandulares esparsas
  - **C** = mamas heterogeneamente densas
  - **D** = mamas extremamente densas

**Mapeie variações de texto:**
- "lipossubstituído", "adiposo" → A
- "densidade heterogênea", "parcialmente denso" → C
- "extremamente denso", "padrão denso" → D

### descricao_achados (ARRAY)

**CRÍTICO:** Cada achado = 1 objeto no array.

Se laudo descreve:
- 2 nódulos → 2 objetos
- 1 nódulo + calcificações → 2 objetos
- Múltiplas calcificações na mesma mama → 1 objeto
- **Laudo normal/sem achados → array vazio `[]`**

#### Para cada achado:

**id_achado:** identificador único (ex: "achado_1", "achado_2")

**tipo_achado:** `massa` | `calcificacoes` | `assimetrias` | `distorcoes_arquiteturais` | `alteracoes_associadas`

**localizacao:**
- `lateralidade`: `direita` | `esquerda`
- `quadrante`: `superior_externo` | `superior_interno` | `inferior_externo` | `inferior_interno` | `central_retroareolar`
  
  **Mapeie:** QSE=superior_externo, QSI=superior_interno, QIE=inferior_externo, QII=inferior_interno

- `coordenadas_polares_mamilo`: distância em mm, posição em horas (1-12)
- `profundidade`: `anterior` | `media` | `posterior` | `null`
- `distancia_mamilo_mm`: float se mencionado
- `correspondencia_achado_clinico`: texto livre se houver correlação com achado palpável

**massa:** (preencher apenas se tipo_achado = massa)
- `forma`: `oval` | `redonda` | `irregular` | `null`
- `margens`: 
  - `circunscrita` = bem definida
  - `obscurecida` = parcialmente oculta
  - `microlobulada` = pequenas lobulações
  - `indistinta_mal_definida` = mal definida, imprecisa
  - `espiculada` = espículas radiadas
- `densidade`: `alta_densidade` | `isodensa_densidade_igual` | `baixa_densidade` | `contem_gordura` | `null`
- `confianca`: 0.0-1.0

**calcificacoes:** (preencher apenas se tipo_achado = calcificacoes)
- `morfologia_tipo`: `tipicamente_benigna` | `morfologia_suspeita` | `null`
- `morfologia_descricao`:
  - **Benignas:** `anelar`, `redonda`, `pele`, `vascular`, `grosseira_pipoca`, `distrofica`, `leite_calcio`, `suturas`, `outras_tipicamente_benignas`
  - **Suspeitas:** `heterogeneamente_grosseiras`, `amorfas`, `finamente_pleomorficas`, `lineares_finas`, `ramificadas`
- `padrao_distribuicao`: `agrupadas` | `segmentar` | `regional` | `difusa` | `linear` | `null`
- `confianca`: 0.0-1.0

**assimetrias:**
- `tipo`: `aumento_global` | `aumento_focal` | `null`

**distorcoes_arquiteturais:**
- `tipo`: `com_centro_radiotransparente` | `com_centro_opaco` | `null`

**tamanho:**
- `maior_diametro_mm`: float
- `comparacao_exame_anterior`:
  - `comparavel`: true se foi possível comparar
  - `data_exame_anterior`: string
  - `evolucao`: `estavel` | `aumentou` | `diminuiu` | `novo` | `nao_comparavel`

**alteracoes_associadas:** array com alterações presentes (valores permitidos)
- `retracao_cutanea`
- `espessamento_cutaneo`
- `espessamento_trabecular`
- `retracao_mamilo`
- `adenopatia_axilar`
- `outras`

**Exemplos:**
- Com alterações: `["espessamento_cutaneo", "retracao_mamilo"]`
- Sem alterações: `[]`

### categorias_diagnosticas_conclusao_laudo

**categoria_birads:** `0` | `1` | `2` | `3` | `4` | `5` | `6`

**BI-RADS:**
- **0** = Avaliação adicional necessária
- **1** = Negativo (sem achados)
- **2** = Achado benigno
- **3** = Provavelmente benigno (<2% malignidade)
- **4** = Suspeito (biópsia indicada)
- **5** = Altamente sugestivo de malignidade
- **6** = Malignidade comprovada histologicamente

**detalhamento:**
Preencha apenas campos relevantes para a categoria atribuída:

- `categoria_0_recursos_adicionais`: array com recursos solicitados (valores permitidos)
  - `compressao_localizada`
  - `magnificacao`
  - `outras_incidencias`
  - `tomossintese`
  - `ultrassom`
  - `solicitar_imagens_previas`
  - Exemplo: `["ultrassom", "magnificacao"]` ou `[]`

- `categoria_1_2_seguimento_meses`: `12` | `24` | `null`

- `categoria_3_conduta`: `seguimento_6_meses` | `biopsia_opcional`

- `categoria_4_5_biopsia`: tipo de biópsia indicada
  - Opções: `guiada_estereotaxia`, `guiada_ultrassom`, `guiada_tomossintese`, `core`, `vacuum`, `null`

- `categoria_6_confirmacao_histopatologica`: texto com resultado prévio

### conclusoes_texto_livre
- `texto`: conclusão/impressão diagnóstica do laudo (texto original)

---

## CHECKLIST OBRIGATÓRIO

Antes de retornar, verifique:

1. ✅ JSON válido (sem erros de sintaxe)
2. ✅ Apenas valores permitidos no template (nada inventado)
3. ✅ Arrays vazios como `[]` quando não há itens (não omitir arrays)
4. ✅ `null` para campos opcionais sem informação
5. ✅ Booleanos como `true`/`false` (não strings "true"/"false")
6. ✅ Números como float/int (não strings "12.5")
7. ✅ `confianca` entre 0.0 e 1.0
8. ✅ Cada achado em objeto separado no array `descricao_achados`
9. ✅ `anotacoes_llm: []` quando não houver dúvidas
10. ✅ Nenhum texto fora do JSON

---

## EXEMPLO DE OUTPUT

```json
{
  "cd_atendimento": "202410001",
  "dados_pessoais": {
    "peso": null,
    "altura": null,
    "imc": null,
    "circunferencia_cintura": null,
    "patologias": null,
    "anotacoes_llm": [],
    "confianca": 1.0
  },
  "setting": {
    "tipo": "mamografia_diagnostica_mulher_sintomatica",
    "outro_especificar": null,
    "anotacoes_llm": [],
    "confianca": 0.95
  },
  "comparacao_exames_previos": {
    "disponivel": true,
    "exame_data": "2023-10-15",
    "imagens_disponiveis": true,
    "laudos_disponiveis": true,
    "anotacoes_llm": [],
    "confianca": 1.0
  },
  "anamnese_contexto_clinico": {
    "anamnese": {
      "historia_familiar_clinica_geral": {
        "terapia_reposicao_hormonal": false,
        "sobrevivente_linfoma_radioterapia_toracica": false,
        "historia_familiar_cancer_mama": {
          "presente": false,
          "quem": null,
          "idade": null
        },
        "mutacoes_geneticas": {
          "BRCA1": false,
          "BRCA2": false,
          "TP53_sindrome_li_fraumeni": false,
          "PTEN_sindrome_cowden": false,
          "CDH1": false,
          "STK11_sindrome_peutz_jeghers": false,
          "ATM": false,
          "CHEK2": false,
          "PALB2": false,
          "outros_especificar": null
        },
        "avaliacao_risco_cancer_mama_opcional": null
      },
      "historia_clinica_mama": {
        "biopsia_percutanea_previa": {
          "realizada": false,
          "localizacao": null
        },
        "cirurgia_previa_lesoes_benignas": {
          "realizada": false,
          "localizacao": null
        },
        "mastoplastia_aditiva_previa": {
          "realizada": false,
          "localizacao": null
        },
        "mastoplastia_redutora_previa": {
          "realizada": false,
          "localizacao": null
        },
        "outro": null,
        "se_algum_especificar_localizacao": null
      }
    },
    "questao_diagnostica": ["nodulo_mama"],
    "questao_diagnostica_outro": null,
    "anotacoes_llm": [],
    "confianca": 1.0
  },
  "tecnica": {
    "lateralidade": "bilateral",
    "tipo_mamografia": "mamografia_digital_FFDM",
    "outro_especificar": null,
    "dose_radiacao_mGy": null,
    "anotacoes_llm": [],
    "confianca": 0.95
  },
  "padrao_parenquimatoso": {
    "classificacao_ACR": "C",
    "avaliacao_quantitativa_automatica": null,
    "anotacoes_llm": [
      "Laudo descreve 'mamas heterogeneamente densas' - classificado como ACR C"
    ],
    "confianca": 0.9
  },
  "descricao_achados": [
    {
      "id_achado": "achado_1",
      "localizacao": {
        "lateralidade": "direita",
        "quadrante": "superior_externo",
        "coordenadas_polares_mamilo": {
          "distancia_mm": 35.0,
          "posicao_horaria": 2
        },
        "profundidade": null,
        "distancia_mamilo_mm": 35.0,
        "correspondencia_achado_clinico": "Nódulo palpável"
      },
      "tipo_achado": "massa",
      "massa": {
        "forma": "irregular",
        "margens": "espiculada",
        "densidade": "alta_densidade",
        "confianca": 0.95
      },
      "calcificacoes": {
        "morfologia_tipo": null,
        "morfologia_descricao": null,
        "padrao_distribuicao": null,
        "confianca": null
      },
      "assimetrias": {
        "tipo": null,
        "confianca": null
      },
      "distorcoes_arquiteturais": {
        "tipo": null,
        "confianca": null
      },
      "tamanho": {
        "maior_diametro_mm": 12.0,
        "comparacao_exame_anterior": {
          "comparavel": true,
          "data_exame_anterior": "2023-10-15",
          "evolucao": "novo"
        }
      },
      "alteracoes_associadas": [],
      "anotacoes_llm": []
    }
  ],
  "categorias_diagnosticas_conclusao_laudo": {
    "categoria_birads": "4",
    "detalhamento": {
      "categoria_0_recursos_adicionais": [],
      "categoria_1_2_seguimento_meses": null,
      "categoria_3_conduta": null,
      "categoria_4_5_biopsia": "guiada_ultrassom",
      "categoria_6_confirmacao_histopatologica": null
    },
    "anotacoes_llm": [],
    "confianca": 1.0
  },
  "conclusoes_texto_livre": {
    "texto": "Nódulo irregular espiculado de alta densidade em QSE da mama direita medindo 12mm. BI-RADS 4. Indicada biópsia guiada por ultrassom.",
    "anotacoes_llm": [],
    "confianca": 1.0
  }
}
```

---

## EXEMPLO: LAUDO NORMAL (SEM ACHADOS PATOLÓGICOS)

Todo laudo deve ser estruturado completo. Quando não há achados patológicos:
- TODOS os campos são preenchidos normalmente
- `descricao_achados`: `[]` (array vazio)
- `categoria_birads`: `"1"` (negativo) ou `"2"` (benigno - ex: linfonodo intramamário)
- Composição do parênquima (ACR) sempre é descrita

**Exemplo:**

```json
{
  "cd_atendimento": "202410002",
  "dados_pessoais": {
    "peso": null,
    "altura": null,
    "imc": null,
    "circunferencia_cintura": null,
    "patologias": null,
    "anotacoes_llm": [],
    "confianca": 1.0
  },
  "setting": {
    "tipo": "avaliacao_rastreamento_organizado",
    "outro_especificar": null,
    "anotacoes_llm": [],
    "confianca": 1.0
  },
  "comparacao_exames_previos": {
    "disponivel": false,
    "exame_data": null,
    "imagens_disponiveis": false,
    "laudos_disponiveis": false,
    "anotacoes_llm": [],
    "confianca": 1.0
  },
  "anamnese_contexto_clinico": {
    "anamnese": {
      "historia_familiar_clinica_geral": {
        "terapia_reposicao_hormonal": false,
        "sobrevivente_linfoma_radioterapia_toracica": false,
        "historia_familiar_cancer_mama": {
          "presente": false,
          "quem": null,
          "idade": null
        },
        "mutacoes_geneticas": {
          "BRCA1": false,
          "BRCA2": false,
          "TP53_sindrome_li_fraumeni": false,
          "PTEN_sindrome_cowden": false,
          "CDH1": false,
          "STK11_sindrome_peutz_jeghers": false,
          "ATM": false,
          "CHEK2": false,
          "PALB2": false,
          "outros_especificar": null
        },
        "avaliacao_risco_cancer_mama_opcional": null
      },
      "historia_clinica_mama": {
        "biopsia_percutanea_previa": {
          "realizada": false,
          "localizacao": null
        },
        "cirurgia_previa_lesoes_benignas": {
          "realizada": false,
          "localizacao": null
        },
        "mastoplastia_aditiva_previa": {
          "realizada": false,
          "localizacao": null
        },
        "mastoplastia_redutora_previa": {
          "realizada": false,
          "localizacao": null
        },
        "outro": null,
        "se_algum_especificar_localizacao": null
      }
    },
    "questao_diagnostica": ["paciente_assintomatica"],
    "questao_diagnostica_outro": null,
    "anotacoes_llm": [],
    "confianca": 1.0
  },
  "tecnica": {
    "lateralidade": "bilateral",
    "tipo_mamografia": "mamografia_digital_FFDM",
    "outro_especificar": null,
    "dose_radiacao_mGy": null,
    "anotacoes_llm": [],
    "confianca": 1.0
  },
  "padrao_parenquimatoso": {
    "classificacao_ACR": "B",
    "avaliacao_quantitativa_automatica": null,
    "anotacoes_llm": [],
    "confianca": 1.0
  },
  "descricao_achados": [],
  "categorias_diagnosticas_conclusao_laudo": {
    "categoria_birads": "1",
    "detalhamento": {
      "categoria_0_recursos_adicionais": [],
      "categoria_1_2_seguimento_meses": "12",
      "categoria_3_conduta": null,
      "categoria_4_5_biopsia": null,
      "categoria_6_confirmacao_histopatologica": null
    },
    "anotacoes_llm": [],
    "confianca": 1.0
  },
  "conclusoes_texto_livre": {
    "texto": "Mamas com padrão fibroglandular disperso (ACR B). Ausência de nódulos, calcificações suspeitas ou outras alterações. BI-RADS 1 - negativo. Controle anual.",
    "anotacoes_llm": [],
    "confianca": 1.0
  }
}
```

---

**AGORA ESTRUTURE O LAUDO COMPLETO SEGUINDO O TEMPLATE. RETORNE APENAS O JSON.**
