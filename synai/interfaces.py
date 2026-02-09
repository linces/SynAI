from typing import Protocol, Dict, Any, Optional

class LLMProvider(Protocol):
    """Protocolo que qualquer driver de IA deve implementar para o SynAI."""
    
    async def generate(self, prompt: str, model: str, **kwargs) -> str:
        """
        Gera uma resposta textual para o prompt dado.
        
        Args:
            prompt: O texto de entrada.
            model: O identificador do modelo (ex: 'claude-3-opus').
            kwargs: Parâmetros extras (temperatura, max_tokens, etc).
            
        Returns:
            A string de resposta gerada.
        """
        ...
    
    async def get_embedding(self, text: str) -> Optional[list[float]]:
        """
        [Opcional] Gera vetor de embedding para o texto.
        """
        ...
