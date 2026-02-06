import json
import logging
import asyncio
from typing import Dict, List, Optional, Callable

from .discovery import MeshDiscovery

class MeshNode:
    """
    Representa um nó na Malha Cognitiva SynAI.
    Capaz de descobrir pares, enviar mensagens e processar comandos remotos.
    Agora com suporte a Descoberta Automática (UDP).
    """
    def __init__(self, node_id: str, role: str = "worker", port: int = 8000):
        self.node_id = node_id
        self.role = role
        self.port = port
        self.peers: List[Dict] = []
        self.handlers: Dict[str, Callable] = {}
        self.logger = logging.getLogger(f"SynAI.Mesh.{node_id}")
        self.discovery = MeshDiscovery(node_id, port)

    def scan_network(self):
        """Busca ativa por pares na rede local."""
        self.logger.info("Iniciando varredura de rede...")
        found = self.discovery.scan(duration=2)
        for peer in found:
            self.register_peer(peer["id"], peer["url"], peer["role"])
        return len(found)

    def announce_presence(self):
        """Anuncia presença na rede."""
        self.discovery.announce()

    def register_peer(self, peer_id: str, url: str, role: str = "unknown"):
        """Registra um novo nó conhecido na malha."""
        peer = {"id": peer_id, "url": url, "role": role, "status": "unknown"}
        self.peers.append(peer)
        self.logger.info(f"Peer registrado: {peer_id} ({role}) em {url}")

    def on_message(self, action: str, handler: Callable):
        """Registra um callback para uma ação específica."""
        self.handlers[action] = handler

    async def process_payload(self, sender_id: str, payload: dict) -> dict:
        """Processa um pacote de dados recebido via rede."""
        action = payload.get("action")
        content = payload.get("content")
        
        self.logger.info(f"Recebido '{action}' de {sender_id}")

        if action == "handshake":
            return self._handle_handshake(sender_id, content)
        
        if action in self.handlers:
            try:
                result = await self.handlers[action](sender_id, content)
                return {"status": "success", "data": result}
            except Exception as e:
                self.logger.error(f"Erro ao processar {action}: {e}")
                return {"status": "error", "reason": str(e)}

        return {"status": "ignored", "reason": "action_unknown"}

    def _handle_handshake(self, sender_id: str, content: dict):
        return {
            "status": "accepted",
            "node_id": self.node_id,
            "role": self.role,
            "message": "SynAI Mesh Connection Established"
        }

    async def broadcast(self, action: str, content: dict):
        """Envia uma mensagem para todos os peers conhecidos (Simulação por enquanto)."""
        # Futuro: Implementar HTTP requests reais aqui usando requests ou aiohttp
        for peer in self.peers:
            self.logger.info(f"Broadcasting {action} to {peer['id']}...")
