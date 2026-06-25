from typing import Protocol, Optional


class LLMProvider(Protocol):
    """
    Protocolo que qualquer driver de IA deve implementar para o SynAI.
    Todos os providers no pacote synai.providers satisfazem este protocolo.
    """

    provider_name: str
    """Identificador único do provider (ex: 'anthropic', 'deepseek')."""

    def is_available(self) -> bool:
        """
        Retorna True se o provider está configurado e pronto para uso.
        Tipicamente verifica se a API key está presente.
        """
        ...

    async def generate(self, prompt: str, model: str, **kwargs) -> str:
        """
        Gera uma resposta textual para o prompt dado.

        Args:
            prompt:     O texto de entrada.
            model:      O identificador do modelo (ex: 'deepseek-chat').
            max_tokens: Número máximo de tokens na resposta (kwarg).
            temperature: Temperatura de amostragem (kwarg).
            **kwargs:   Parâmetros extras aceitos pelo provider.

        Returns:
            A string de resposta gerada.
        """
        ...

    async def get_embedding(self, text: str) -> Optional[list[float]]:
        """
        [Opcional] Gera vetor de embedding para o texto.

        Returns:
            Lista de floats representando o embedding, ou None se não suportado.
        """
        ...
