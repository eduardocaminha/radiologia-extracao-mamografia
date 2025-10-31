"""
Classe principal para extração estruturada de laudos de mamografia
"""

import json
import requests
from pathlib import Path
from typing import Dict, Optional, Any
from .validators import validar_laudo_estruturado


class LaudoExtractor:
    """
    Extrator de laudos de mamografia usando LLM (Phi-4 via Ollama)
    """
    
    def __init__(
        self,
        model: str = "phi4:14b",
        template_path: str = "config/template.json",
        prompt_path: str = "config/prompt_extracao_mamografia.md",
        ollama_host: str = "http://localhost:11434"
    ):
        """
        Inicializa o extrator
        
        Args:
            model: Nome do modelo Ollama
            template_path: Caminho para template.json
            prompt_path: Caminho para prompt .md
            ollama_host: URL do servidor Ollama
        """
        self.model = model
        self.ollama_host = ollama_host
        self.ollama_url = f"{ollama_host}/api/generate"
        
        # Carregar template e prompt
        self.template = self._carregar_json(template_path)
        self.prompt_base = self._carregar_texto(prompt_path)
        
        # Verificar conexão com Ollama
        self._verificar_ollama()
    
    def _carregar_json(self, caminho: str) -> Dict:
        """Carrega arquivo JSON"""
        with open(caminho, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _carregar_texto(self, caminho: str) -> str:
        """Carrega arquivo texto"""
        with open(caminho, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _verificar_ollama(self):
        """Verifica se Ollama está rodando"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            if response.status_code != 200:
                raise ConnectionError("Ollama não está respondendo")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(
                f"Não foi possível conectar ao Ollama em {self.ollama_host}. "
                f"Certifique-se de que o serviço está rodando. Erro: {e}"
            )
    
    def processar(
        self,
        laudo_texto: str,
        cd_atendimento: Optional[str] = None,
        temperatura: float = 0.1,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Processa um laudo e retorna estrutura JSON
        
        Args:
            laudo_texto: Texto do laudo a processar
            cd_atendimento: Código do atendimento (opcional)
            temperatura: Temperatura do modelo (0-1, menor = mais determinístico)
            max_tokens: Máximo de tokens na resposta
            
        Returns:
            Dict com laudo estruturado
        """
        # Montar prompt completo
        prompt_completo = self._montar_prompt(laudo_texto)
        
        # Chamar Ollama
        payload = {
            "model": self.model,
            "prompt": prompt_completo,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": temperatura,
                "num_predict": max_tokens
            }
        }
        
        try:
            response = requests.post(
                self.ollama_url,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            # Extrair JSON da resposta
            resultado_raw = response.json()
            laudo_estruturado = json.loads(resultado_raw["response"])
            
            # Adicionar cd_atendimento se fornecido
            if cd_atendimento:
                laudo_estruturado["cd_atendimento"] = cd_atendimento
            
            # Validar
            erros = validar_laudo_estruturado(laudo_estruturado, self.template)
            if erros:
                laudo_estruturado["_validacao_erros"] = erros
            
            return laudo_estruturado
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Erro na requisição ao Ollama: {e}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Resposta do modelo não é JSON válido: {e}")
        except Exception as e:
            raise RuntimeError(f"Erro ao processar laudo: {e}")
    
    def _montar_prompt(self, laudo_texto: str) -> str:
        """Monta prompt completo com template e laudo"""
        template_str = json.dumps(self.template, indent=2, ensure_ascii=False)
        
        return f"""{self.prompt_base}

## TEMPLATE JSON:

```json
{template_str}
```

---

## LAUDO A ESTRUTURAR:

{laudo_texto}

---

RETORNE APENAS O JSON ESTRUTURADO:
"""
    
    def processar_lote(
        self,
        laudos: list,
        campo_texto: str = "texto",
        campo_cd: Optional[str] = None,
        verbose: bool = True
    ) -> list:
        """
        Processa múltiplos laudos
        
        Args:
            laudos: Lista de dicts com laudos
            campo_texto: Nome do campo contendo texto do laudo
            campo_cd: Nome do campo com código de atendimento (opcional)
            verbose: Mostrar progresso
            
        Returns:
            Lista de laudos estruturados
        """
        resultados = []
        
        if verbose:
            from tqdm import tqdm
            laudos = tqdm(laudos, desc="Processando laudos")
        
        for laudo in laudos:
            try:
                texto = laudo[campo_texto]
                cd = laudo.get(campo_cd) if campo_cd else None
                
                resultado = self.processar(texto, cd_atendimento=cd)
                resultado["_original"] = laudo
                resultado["_sucesso"] = True
                
            except Exception as e:
                resultado = {
                    "_original": laudo,
                    "_sucesso": False,
                    "_erro": str(e)
                }
            
            resultados.append(resultado)
        
        return resultados

