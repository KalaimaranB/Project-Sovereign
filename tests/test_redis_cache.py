import pytest
import pytest_asyncio
import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gamespy.redis_cache import RedisGamespyCache

@pytest_asyncio.fixture
async def cache_engine():
    """Establish active connect handler to docker instance."""
    c = RedisGamespyCache("redis://localhost:6379/0")
    await c.connect()
    
    # CLEAR DB FOR CLEAN RUN
    await c.r.flushdb()
    
    yield c
    
    await c.close()

@pytest.mark.asyncio
async def test_redis_server_lifecycle(cache_engine):
    """Ensures atomics write, read, and scan correctly."""
    c = cache_engine
    
    mock_data = {"publicip": "127.0.0.1", "numplayers": 2}
    
    # Insert 2 distinct sessions
    await c.upsert_server("supermario_ds", 999, mock_data)
    await c.upsert_server("supermario_ds", 1000, {"publicip": "10.0.0.1"})
    
    # Fetch aggregate
    servers = await c.get_all_servers_for_game("supermario_ds")
    assert len(servers) == 2
    
    # Verify correct deserialization
    ips = [s['publicip'] for s in servers]
    assert "127.0.0.1" in ips
    assert "10.0.0.1" in ips
    
    # Delete
    await c.delete_server("supermario_ds", 999)
    servers_after = await c.get_all_servers_for_game("supermario_ds")
    assert len(servers_after) == 1
    assert servers_after[0]['publicip'] == "10.0.0.1"

@pytest.mark.asyncio
async def test_redis_ttl_expiration(cache_engine):
    """Confirms short TTL automatically erases stale records effortlessly."""
    c = cache_engine
    
    # Set aggressive TTL of 1 second
    await c.upsert_server("ttl_test", 777, {"state": "live"}, ttl_seconds=1)
    
    # Immediate confirm
    exists = await c.get_all_servers_for_game("ttl_test")
    assert len(exists) == 1
    
    # Wait and observe
    await asyncio.sleep(1.2)
    
    vanished = await c.get_all_servers_for_game("ttl_test")
    assert len(vanished) == 0, "Ghost entry failed to evaporate! TTL failure detected."

@pytest.mark.asyncio
async def test_redis_natneg_aggregation(cache_engine):
    """Validates list pipelining for NAT negotiation packet aggregation."""
    c = cache_engine
    cookie = 123456
    
    # Aggregation
    await c.add_natneg_server(cookie, {"client": "a"})
    await c.add_natneg_server(cookie, {"client": "b"})
    
    # Retrieval
    results = await c.get_natneg_servers(cookie)
    assert len(results) == 2
    assert results[0]['client'] == "a"
    assert results[1]['client'] == "b"
    
    # Clear
    await c.delete_natneg_server(cookie)
    cleared = await c.get_natneg_servers(cookie)
    assert len(cleared) == 0
