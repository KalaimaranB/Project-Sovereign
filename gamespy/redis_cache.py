import json
import logging
import redis.asyncio as async_redis
import redis
from typing import List, Dict, Any

try:
    from gamespy.i_gs_cache import IGamespyCache
except ImportError:
    # Fallback support for direct runtime invocation or older package topologies
    from i_gs_cache import IGamespyCache

logger = logging.getLogger('RedisCache')

class RedisGamespyCache(IGamespyCache):
    """
    Atomic Redis-backed dynamic cache fulfillment.
    Leverages distinct keys per server to grant implicit fine-grain TTL expiration policies.
    """
    def __init__(self, url=None):
        import os
        self.url = url or os.environ.get("REDIS_URL") or "redis://redis:6379/0"
        self.r = None

    async def connect(self):
        """Establishes native redis pool."""
        if not self.r:
            self.r = async_redis.from_url(self.url, decode_responses=True)
            # Ping to verify availability
            await self.r.ping()
            logger.info("Successfully connected to Redis cache matrix at %s", self.url)

    async def close(self):
        """Graceful connection release."""
        if self.r:
            await self.r.aclose()
            self.r = None

    # --- Server Management with Auto-Evaporation ---

    def _make_srv_key(self, gamename: str, session_id: int) -> str:
        return f"gs:srv:{gamename}:{session_id}"

    async def upsert_server(self, gamename: str, session_id: int, server_data: Dict[str, Any], ttl_seconds: int = 60):
        if not self.r:
             await self.connect()
             
        key = self._make_srv_key(gamename, session_id)
        payload = json.dumps(server_data)
        
        # Atomic SET with EXPIRE
        await self.r.set(key, payload, ex=ttl_seconds)

    async def delete_server(self, gamename: str, session_id: int):
        if not self.r:
             await self.connect()
        
        key = self._make_srv_key(gamename, session_id)
        await self.r.delete(key)

    async def get_all_servers_for_game(self, gamename: str = None) -> List[Dict[str, Any]]:
        if not self.r:
             await self.connect()
             
        if gamename:
             pattern = f"gs:srv:{gamename}:*"
        else:
             pattern = "gs:srv:*:*"
        keys = []
        
        # Utilize async cursor scan to strictly prevent blocking production threads
        async for key in self.r.scan_iter(match=pattern):
             keys.append(key)
             
        if not keys:
             return []
             
        # Batch fetch using multiple GET pipeline
        values = await self.r.mget(keys)
        
        results = []
        for v in values:
             if v:
                 try:
                     results.append(json.loads(v))
                 except Exception:
                     pass # Skip corrupted serialization
        return results

    # --- NAT Negotiation Bridges using Atomic Lists ---

    def _make_nat_key(self, cookie: int) -> str:
        return f"gs:nat:{cookie}"

    async def add_natneg_server(self, cookie: int, server_data: Dict[str, Any], ttl_seconds: int = 300):
        if not self.r:
             await self.connect()
             
        key = self._make_nat_key(cookie)
        payload = json.dumps(server_data)
        
        # Use List RPUSH followed by direct EXPIRE
        async with self.r.pipeline(transaction=True) as pipe:
             pipe.rpush(key, payload)
             pipe.expire(key, ttl_seconds)
             await pipe.execute()

    async def get_natneg_servers(self, cookie: int) -> List[Dict[str, Any]]:
        if not self.r:
             await self.connect()
             
        key = self._make_nat_key(cookie)
        raw_list = await self.r.lrange(key, 0, -1)
        
        results = []
        for val in raw_list:
             try:
                  results.append(json.loads(val))
             except Exception:
                  pass
        return results

    async def delete_natneg_server(self, cookie: int):
        if not self.r:
             await self.connect()
             
        key = self._make_nat_key(cookie)
        await self.r.delete(key)

# --- Synchronous Variant for Legacy Systems Bridge ---

class RedisGamespyCacheSync:
    """
    Synchronous realization ensuring total compatibility across existing legacy components 
    that utilize traditional procedural threading or Twisted reactor hooks without native async loops.
    """
    def __init__(self, url=None):
        import os
        self.url = url or os.environ.get("REDIS_URL") or "redis://redis:6379/0"
        self.r = None

    def connect(self):
        if not self.r:
            self.r = redis.from_url(self.url, decode_responses=True)
            self.r.ping()

    def close(self):
        if self.r:
            self.r.close()
            self.r = None

    def _make_srv_key(self, gamename: str, session_id: int) -> str:
        return f"gs:srv:{gamename}:{session_id}"

    def upsert_server(self, gamename: str, session_id: int, server_data: Dict[str, Any], ttl_seconds: int = 60):
        if not self.r:
             self.connect()
        key = self._make_srv_key(gamename, session_id)
        self.r.set(key, json.dumps(server_data), ex=ttl_seconds)

    def delete_server(self, gamename: str, session_id: int):
        if not self.r:
             self.connect()
        self.r.delete(self._make_srv_key(gamename, session_id))

    def get_all_servers_for_game(self, gamename: str = None) -> List[Dict[str, Any]]:
        if not self.r:
             self.connect()
        if gamename:
             pattern = f"gs:srv:{gamename}:*"
        else:
             pattern = "gs:srv:*:*"
        keys = list(self.r.scan_iter(match=pattern))
        if not keys:
             return []
        values = self.r.mget(keys)
        results = []
        for v in values:
             if v:
                 try:
                     results.append(json.loads(v))
                 except:
                     pass
        return results

    def _make_nat_key(self, cookie: int) -> str:
        return f"gs:nat:{cookie}"

    def add_natneg_server(self, cookie: int, server_data: Dict[str, Any], ttl_seconds: int = 300):
        if not self.r:
             self.connect()
        key = self._make_nat_key(cookie)
        with self.r.pipeline(transaction=True) as pipe:
             pipe.rpush(key, json.dumps(server_data))
             pipe.expire(key, ttl_seconds)
             pipe.execute()

    def get_natneg_servers(self, cookie: int) -> List[Dict[str, Any]]:
        if not self.r:
             self.connect()
        raw_list = self.r.lrange(self._make_nat_key(cookie), 0, -1)
        results = []
        for val in raw_list:
             try:
                  results.append(json.loads(val))
             except:
                  pass
        return results

    def delete_natneg_server(self, cookie: int):
        if not self.r:
             self.connect()
        self.r.delete(self._make_nat_key(cookie))
