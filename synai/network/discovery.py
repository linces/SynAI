import socket
import json
import logging
import asyncio
from typing import List, Dict

class MeshDiscovery:
    """
    Componente responsável por encontrar outros nós SynAI na rede local
    via UDP Broadcast (Porta 54321).
    """
    BROADCAST_PORT = 54321
    
    def __init__(self, node_id: str, http_port: int = 8000):
        self.node_id = node_id
        self.http_port = http_port
        self.logger = logging.getLogger(f"SynAI.Discovery.{node_id}")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.settimeout(0.5)

    def announce(self):
        """Grita na rede: 'EU ESTOU AQUI!'"""
        message = json.dumps({
            "type": "HELLO",
            "id": self.node_id,
            "port": self.http_port
        }).encode('utf-8')
        
        try:
            self.sock.sendto(message, ('<broadcast>', self.BROADCAST_PORT))
            self.logger.info(f"Ping UDP enviado para porta {self.BROADCAST_PORT}")
        except Exception as e:
            self.logger.error(f"Erro ao anunciar presença: {e}")

    def scan(self, duration: int = 2) -> List[Dict]:
        """Escuta a rede por 'duration' segundos procurando outros nós."""
        found_peers = []
        self.logger.info(f"Escutando frequências UDP por {duration}s...")
        
        # Cria um socket temporário para escutar
        listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listener.bind(('', self.BROADCAST_PORT))
        listener.settimeout(duration)
        
        try:
            while True:
                data, addr = listener.recvfrom(1024)
                payload = json.loads(data.decode('utf-8'))
                
                if payload.get("type") == "HELLO" and payload.get("id") != self.node_id:
                    peer_url = f"http://{addr[0]}:{payload['port']}"
                    found_peers.append({
                        "id": payload["id"],
                        "url": peer_url,
                        "role": "discovered"
                    })
                    self.logger.info(f"Nó detectado via UDP: {payload['id']} em {peer_url}")
        except socket.timeout:
            pass
        except Exception as e:
            self.logger.error(f"Erro no scan: {e}")
        finally:
            listener.close()
            
        return found_peers
