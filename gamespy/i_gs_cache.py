from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class IGamespyCache(ABC):
    """
    Abstract interface for GameSpy volatile memory storage.
    Replaces raw memory dictionary sharing to support distributed node topologies.
    """
    
    @abstractmethod
    async def connect(self):
        """Establish foundational connection matrix to backend."""
        pass
        
    @abstractmethod
    async def close(self):
        """Gracefully sever connections."""
        pass

    # --- Game Lobby Management (Server Browser) ---
    
    @abstractmethod
    async def upsert_server(self, gamename: str, session_id: int, server_data: Dict[str, Any], ttl_seconds: int = 60):
        """
        Atomically creates or refreshes dynamic server entry inside explicit game namespace.
        Applies absolute expiration to ensure garbage auto-collection of ghost entries.
        """
        pass
        
    @abstractmethod
    async def delete_server(self, gamename: str, session_id: int):
        """Immediately destroys cached metadata belonging to terminated session."""
        pass
        
    @abstractmethod
    async def get_all_servers_for_game(self, gamename: str) -> List[Dict[str, Any]]:
        """Retrieves entire snapshot of live servers mapped to specific identifiers."""
        pass

    # --- NAT Negotiation Stateful Bridges ---
    
    @abstractmethod
    async def add_natneg_server(self, cookie: int, server_data: Dict[str, Any], ttl_seconds: int = 300):
        """Aggregates server payload into transient buffer identified by transaction cookie."""
        pass
        
    @abstractmethod
    async def get_natneg_servers(self, cookie: int) -> List[Dict[str, Any]]:
        """Retrieves aggregate listing associated with designated NAT cookie."""
        pass
        
    @abstractmethod
    async def delete_natneg_server(self, cookie: int):
        """Expunges collective NAT negotiation buffer upon request completion."""
        pass
