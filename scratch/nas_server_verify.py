import threading
import time
import json
import urllib.request
import urllib.parse
from nas_server import NasServer
from gamespy.pg_database import PostgresGamespyDatabase
import asyncio
import dwc_config
import sys

def run_verification():
    print("--- COMMENCING TARGET #2 VERIFICATION (NasServer) ---")
    
    # 1. Prepare DB
    db = PostgresGamespyDatabase("postgresql://dwc_admin:insecure_dev_password@localhost:5432/gamespy")
    async def setup():
        await db.initialize_database()
        async with db.pool.acquire() as conn:
            await conn.execute("DELETE FROM nas_logins")
        await db.close()
    asyncio.run(setup())
    print("[1] Environment Cleaned.")
    
    # 2. Boot Server
    nas = NasServer()
    server_thread = threading.Thread(target=nas.start, daemon=True)
    server_thread.start()
    
    time.sleep(1)
    print("[2] Server Started.")
    
    # 3. Send Native Request
    addr = dwc_config.get_ip_port('NasServer')
    url = f"http://{addr[0]}:{addr[1]}/ac"
    
    payload = {
        "action": "acctcreate",
        "gamecd": "BATT1",
        "macadr": "aabbccddeeff",
        "devname": "TestUnit"
    }
    
    data = urllib.parse.urlencode(payload).encode('ascii')
    req = urllib.request.Request(url, data=data, method='POST')
    
    print(f"[3] POSTing to {url}...")
    try:
        with urllib.request.urlopen(req) as response:
            resp_data = response.read().decode('utf-8')
            print(f"RAW RESPONSE:\n{resp_data}")
            
            res_dict = urllib.parse.parse_qs(resp_data)
            if 'userid' not in res_dict:
                 print("\n❌ FAILED: No 'userid' returned in response!")
                 sys.exit(1)
            
            uid = res_dict['userid'][0]
            print(f"REGISTERED USER ID: {uid}")
            
            # Final Check
            async def check():
                db2 = PostgresGamespyDatabase("postgresql://dwc_admin:insecure_dev_password@localhost:5432/gamespy")
                await db2.initialize_database()
                row = await db2.get_nas_login_from_userid(uid)
                await db2.close()
                return row
                
            final_data = asyncio.run(check())
            print(f"\nVERIFIED DB ROW: {final_data}")
            
            if final_data is not None:
                print("\n🏆 MASTER TARGET #2 SUCCESS ACHIEVED 🏆")
            else:
                print("\n❌ FAILED: Row missing from Postgres!")
                sys.exit(1)
                
    except Exception as e:
        print(f"\n❌ EXCEPTION CAUGHT: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_verification()
