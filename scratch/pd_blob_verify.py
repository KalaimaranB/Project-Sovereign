import asyncio
from gamespy.pg_database import PostgresGamespyDatabase

async def run():
    print("--- COMMENCING TELEMETRY BLOB ATOMIC UPSERT TEST ---")
    
    db = PostgresGamespyDatabase("postgresql://dwc_admin:insecure_dev_password@localhost:5432/gamespy")
    await db.initialize_database()
    
    # Wipe before test
    async with db.pool.acquire() as conn:
        await conn.execute("DELETE FROM gamestat_profile")
        
    # 1. Perform First Insert
    print("[1] Inserting initial telemetry blob...")
    await db.pd_insert(50001, "index_1", "stats", "initial_data_payload")
    
    r1 = await db.pd_get(50001, "index_1", "stats")
    print(f"Retrieved data: {r1['data']}")
    
    assert r1['data'] == "initial_data_payload"
    
    # 2. Perform Atomic Upsert (Update existing)
    print("[2] Executing atomic overwrite upsert...")
    await db.pd_insert(50001, "index_1", "stats", "UPDATED_PAYLOAD_SUCCESS")
    
    r2 = await db.pd_get(50001, "index_1", "stats")
    print(f"Updated data: {r2['data']}")
    
    assert r2['data'] == "UPDATED_PAYLOAD_SUCCESS"
    
    # 3. Count to ensure NO DUPLICATES (Unique key integrity check)
    async with db.pool.acquire() as conn:
        cnt = await conn.fetchval("SELECT COUNT(*) FROM gamestat_profile")
    print(f"[3] Physical row count: {cnt}")
    
    assert int(cnt) == 1
    print("\n🏆 BLOB PERSISTENCE VICTORY CONFIRMED 🏆")
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(run())
