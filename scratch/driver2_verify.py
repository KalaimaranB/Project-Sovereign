import asyncio
from gamespy.pg_database import PostgresGamespyDatabase

async def test():
    db = PostgresGamespyDatabase("postgresql://dwc_admin:insecure_dev_password@localhost:5432/gamespy")
    await db.initialize_database()
    
    print("TESTING NEXT USER ID...")
    uid = await db.get_next_available_userid()
    print(f"NEXT UID: {uid}")
    
    print("TESTING AUTH TOKEN GEN...")
    token = await db.generate_authtoken("test-user-gen", {"test_key": "value1"})
    print(f"GENERATED TOKEN: {token}")
    
    print("VERIFYING PERSISTENCE...")
    check = await db.get_nas_login_from_userid("test-user-gen")
    print(f"PERSISTED DATA: {check}")
    
    await db.close()

asyncio.run(test())
