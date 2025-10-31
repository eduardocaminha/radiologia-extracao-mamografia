"""
Validadores para laudos estruturados
"""

from typing import Dict, List, Any


def validar_laudo_estruturado(laudo: Dict[str, Any], template: Dict[str, Any]) -> List[str]:
    """
    Valida se o laudo estruturado segue o template
    
    Args:
        laudo: Laudo estruturado para validar
        template: Template de referência
        
    Returns:
        Lista de erros encontrados (vazia se válido)
    """
    erros = []
    
    # Validar campos obrigatórios principais
    campos_obrigatorios = [
        "cd_atendimento",
        "dados_pessoais",
        "setting",
        "comparacao_exames_previos",
        "anamnese_contexto_clinico",
        "tecnica",
        "padrao_parenquimatoso",
        "descricao_achados",
        "categorias_diagnosticas_conclusao_laudo",
        "conclusoes_texto_livre"
    ]
    
    for campo in campos_obrigatorios:
        if campo not in laudo:
            erros.append(f"Campo obrigatório ausente: {campo}")
    
    # Validar BI-RADS
    if "categorias_diagnosticas_conclusao_laudo" in laudo:
        birads = laudo["categorias_diagnosticas_conclusao_laudo"].get("categoria_birads")
        if birads not in ["0", "1", "2", "3", "4", "5", "6"]:
            erros.append(f"BI-RADS inválido: {birads}")
    
    # Validar ACR
    if "padrao_parenquimatoso" in laudo:
        acr = laudo["padrao_parenquimatoso"].get("classificacao_ACR")
        if acr not in ["A", "B", "C", "D", None]:
            erros.append(f"Classificação ACR inválida: {acr}")
    
    # Validar confiança (deve estar entre 0 e 1)
    def validar_confianca_recursivo(obj, caminho=""):
        if isinstance(obj, dict):
            if "confianca" in obj:
                conf = obj["confianca"]
                if not isinstance(conf, (int, float)) or not (0 <= conf <= 1):
                    erros.append(f"Confiança inválida em {caminho}: {conf}")
            for k, v in obj.items():
                validar_confianca_recursivo(v, f"{caminho}.{k}" if caminho else k)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                validar_confianca_recursivo(item, f"{caminho}[{i}]")
    
    validar_confianca_recursivo(laudo)
    
    # Validar arrays de achados
    if "descricao_achados" in laudo:
        achados = laudo["descricao_achados"]
        if not isinstance(achados, list):
            erros.append("descricao_achados deve ser array")
        else:
            for i, achado in enumerate(achados):
                # Validar tipo_achado
                tipo = achado.get("tipo_achado")
                tipos_validos = ["massa", "calcificacoes", "assimetrias", "distorcoes_arquiteturais", "alteracoes_associadas"]
                if tipo not in tipos_validos:
                    erros.append(f"tipo_achado inválido no achado {i}: {tipo}")
                
                # Validar lateralidade
                if "localizacao" in achado:
                    lat = achado["localizacao"].get("lateralidade")
                    if lat not in ["direita", "esquerda", None]:
                        erros.append(f"lateralidade inválida no achado {i}: {lat}")
    
    # Validar técnica
    if "tecnica" in laudo:
        lat = laudo["tecnica"].get("lateralidade")
        if lat not in ["bilateral", "unilateral_direita", "unilateral_esquerda", None]:
            erros.append(f"lateralidade técnica inválida: {lat}")
    
    return erros


def calcular_metricas_confianca(laudo: Dict[str, Any]) -> Dict[str, float]:
    """
    Calcula métricas de confiança do laudo
    
    Args:
        laudo: Laudo estruturado
        
    Returns:
        Dict com métricas (média, mínima, máxima)
    """
    confiancas = []
    
    def extrair_confiancas(obj):
        if isinstance(obj, dict):
            if "confianca" in obj:
                conf = obj["confianca"]
                if isinstance(conf, (int, float)):
                    confiancas.append(float(conf))
            for v in obj.values():
                extrair_confiancas(v)
        elif isinstance(obj, list):
            for item in obj:
                extrair_confiancas(item)
    
    extrair_confiancas(laudo)
    
    if not confiancas:
        return {"media": 0.0, "minima": 0.0, "maxima": 0.0, "count": 0}
    
    return {
        "media": sum(confiancas) / len(confiancas),
        "minima": min(confiancas),
        "maxima": max(confiancas),
        "count": len(confiancas)
    }


def extrair_anotacoes_llm(laudo: Dict[str, Any]) -> List[str]:
    """
    Extrai todas as anotações do LLM do laudo
    
    Args:
        laudo: Laudo estruturado
        
    Returns:
        Lista de todas as anotações encontradas
    """
    anotacoes = []
    
    def extrair_recursivo(obj, caminho=""):
        if isinstance(obj, dict):
            if "anotacoes_llm" in obj and obj["anotacoes_llm"]:
                for anotacao in obj["anotacoes_llm"]:
                    anotacoes.append(f"[{caminho}] {anotacao}")
            for k, v in obj.items():
                extrair_recursivo(v, f"{caminho}.{k}" if caminho else k)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                extrair_recursivo(item, f"{caminho}[{i}]")
    
    extrair_recursivo(laudo)
    return anotacoes

