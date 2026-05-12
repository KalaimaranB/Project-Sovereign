import asyncio
from nas_server import handle_ac_login
from gamespy.pg_database import PostgresGamespyDatabase
from gamespy.pg_database_sync import PostgresGamespyDatabaseSync

def run():
    print("--- COMMENCING UNIT BRIDGE LOGIC VERIFICATION ---")
    
    # 1. Wipe existing
    async def wipe():
        db = PostgresGamespyDatabase("postgresql://dwc_admin:insecure_dev_password@localhost:5432/gamespy")
        await db.initialize_database()
        async with db.pool.acquire() as conn:
            await conn.execute("DELETE FROM nas_logins")
        await db.close()
    asyncio.run(wipe())
    print("[1] DB Freshly Wiped.")
    
    # 2. Instantiate our actual production bridge just like the server does
    bridge = PostgresGamespyDatabaseSync("postgresql://dwc_admin:insecure_dev_password@localhost:5432/gamespy")
    print("[2] PostgresGamespyDatabaseSync online.")
    
    # 3. Invoke the live business logic handler
    fake_post = {
        "userid": "CONSOLE-UNIT-TEST-8888",
        "gamecd": "BATT1",
        "ipaddr": "127.0.0.1"
    }
    
    print("[3] Triggering handle_ac_login direct handler injection...")
    result_dict = handle_ac_login(None, bridge, ("127.0.0.1", 9999), fake_post)
    
    print(f"HANDLER RESPONSE: {result_dict}")
    
    if "token" not in result_dict:
         print("\n❌ FAIL: Handler failed to yield auth token!")
         return
         
    gen_token = result_dict["token"]
    print(f"OBTAINED AUTH TOKEN: {gen_token}")
    
    # 4. Final Postgres lookup verification
    async def verify():
        db2 = PostgresGamespyDatabase("postgresql://dwc_admin:insecure_dev_password@localhost:5432/gamespy")
        await db2.initialize_database()
        row = await db2.get_nas_login_from_userid("CONSOLE-UNIT-TEST-8888")
        await db2.close()
        return row

    final_check = asyncio.run(verify())
    print(f"\n[4] CONFIRMED RECORD IN POSTGRES: {final_check}")
    
    if final_check is not None:
        print("\n🏆 TARGET #2 - PURE LOGIC VICTORY ACHIEVED 🏆")
    else:
        print("\n❌ FAILED: Database row did not persist!")
        
if __name__ == "__main__":
    run()
