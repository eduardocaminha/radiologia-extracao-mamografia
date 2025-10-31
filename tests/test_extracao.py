"""
Testes unitários para extração de laudos
"""

import pytest
import json
from src.validators import validar_laudo_estruturado, calcular_metricas_confianca, extrair_anotacoes_llm


def test_validar_laudo_completo():
    """Testa validação de laudo bem formado"""
    laudo = {
        "cd_atendimento": "2024-001",
        "dados_pessoais": {"peso": None, "altura": None, "imc": None, "circunferencia_cintura": None, "patologias": None, "anotacoes_llm": [], "confianca": 1.0},
        "setting": {"tipo": "avaliacao_rastreamento_organizado", "outro_especificar": None, "anotacoes_llm": [], "confianca": 1.0},
        "comparacao_exames_previos": {"disponivel": False, "exame_data": None, "imagens_disponiveis": False, "laudos_disponiveis": False, "anotacoes_llm": [], "confianca": 1.0},
        "anamnese_contexto_clinico": {"anamnese": {"historia_familiar_clinica_geral": {}, "historia_clinica_mama": {}}, "questao_diagnostica": ["paciente_assintomatica"], "questao_diagnostica_outro": None, "anotacoes_llm": [], "confianca": 1.0},
        "tecnica": {"lateralidade": "bilateral", "tipo_mamografia": "mamografia_digital_FFDM", "outro_especificar": None, "dose_radiacao_mGy": None, "anotacoes_llm": [], "confianca": 1.0},
        "padrao_parenquimatoso": {"classificacao_ACR": "B", "avaliacao_quantitativa_automatica": None, "anotacoes_llm": [], "confianca": 1.0},
        "descricao_achados": [],
        "categorias_diagnosticas_conclusao_laudo": {"categoria_birads": "1", "detalhamento": {}, "anotacoes_llm": [], "confianca": 1.0},
        "conclusoes_texto_livre": {"texto": "Mamografia normal", "anotacoes_llm": [], "confianca": 1.0}
    }
    
    erros = validar_laudo_estruturado(laudo, {})
    assert len(erros) == 0, f"Não deveria ter erros: {erros}"


def test_validar_birads_invalido():
    """Testa detecção de BI-RADS inválido"""
    laudo = {
        "cd_atendimento": "2024-001",
        "dados_pessoais": {},
        "setting": {},
        "comparacao_exames_previos": {},
        "anamnese_contexto_clinico": {},
        "tecnica": {},
        "padrao_parenquimatoso": {},
        "descricao_achados": [],
        "categorias_diagnosticas_conclusao_laudo": {"categoria_birads": "10"},  # Inválido
        "conclusoes_texto_livre": {}
    }
    
    erros = validar_laudo_estruturado(laudo, {})
    assert any("BI-RADS inválido" in erro for erro in erros)


def test_validar_acr_invalido():
    """Testa detecção de ACR inválido"""
    laudo = {
        "cd_atendimento": "2024-001",
        "dados_pessoais": {},
        "setting": {},
        "comparacao_exames_previos": {},
        "anamnese_contexto_clinico": {},
        "tecnica": {},
        "padrao_parenquimatoso": {"classificacao_ACR": "E"},  # Inválido
        "descricao_achados": [],
        "categorias_diagnosticas_conclusao_laudo": {"categoria_birads": "1"},
        "conclusoes_texto_livre": {}
    }
    
    erros = validar_laudo_estruturado(laudo, {})
    assert any("ACR inválida" in erro for erro in erros)


def test_calcular_metricas_confianca():
    """Testa cálculo de métricas de confiança"""
    laudo = {
        "dados_pessoais": {"confianca": 0.9},
        "setting": {"confianca": 0.8},
        "tecnica": {"confianca": 1.0}
    }
    
    metricas = calcular_metricas_confianca(laudo)
    
    assert metricas["count"] == 3
    assert metricas["media"] == pytest.approx(0.9, abs=0.01)
    assert metricas["minima"] == 0.8
    assert metricas["maxima"] == 1.0


def test_extrair_anotacoes_llm():
    """Testa extração de anotações do LLM"""
    laudo = {
        "dados_pessoais": {
            "anotacoes_llm": ["Peso não mencionado"]
        },
        "tecnica": {
            "anotacoes_llm": ["Dose não disponível", "Inferido tipo FFDM"]
        }
    }
    
    anotacoes = extrair_anotacoes_llm(laudo)
    
    assert len(anotacoes) == 3
    assert any("Peso não mencionado" in a for a in anotacoes)
    assert any("Dose não disponível" in a for a in anotacoes)


def test_validar_confianca_fora_range():
    """Testa detecção de confiança fora do range 0-1"""
    laudo = {
        "cd_atendimento": "2024-001",
        "dados_pessoais": {"confianca": 1.5},  # Inválido
        "setting": {},
        "comparacao_exames_previos": {},
        "anamnese_contexto_clinico": {},
        "tecnica": {},
        "padrao_parenquimatoso": {},
        "descricao_achados": [],
        "categorias_diagnosticas_conclusao_laudo": {"categoria_birads": "1"},
        "conclusoes_texto_livre": {}
    }
    
    erros = validar_laudo_estruturado(laudo, {})
    assert any("Confiança inválida" in erro for erro in erros)


def test_validar_tipo_achado_invalido():
    """Testa detecção de tipo de achado inválido"""
    laudo = {
        "cd_atendimento": "2024-001",
        "dados_pessoais": {},
        "setting": {},
        "comparacao_exames_previos": {},
        "anamnese_contexto_clinico": {},
        "tecnica": {},
        "padrao_parenquimatoso": {},
        "descricao_achados": [
            {
                "tipo_achado": "algo_invalido",  # Inválido
                "localizacao": {}
            }
        ],
        "categorias_diagnosticas_conclusao_laudo": {"categoria_birads": "1"},
        "conclusoes_texto_livre": {}
    }
    
    erros = validar_laudo_estruturado(laudo, {})
    assert any("tipo_achado inválido" in erro for erro in erros)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

