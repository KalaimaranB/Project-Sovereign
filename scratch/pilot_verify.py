import asyncio
import json
from gamespy.pg_database import PostgresGamespyDatabase
from gamespy_qr_server import GameSpyQRServer

async def setup_test_data():
    db = PostgresGamespyDatabase("postgresql://dwc_admin:insecure_dev_password@localhost:5432/gamespy")
    await db.initialize_database()
    async with db.pool.acquire() as conn:
        await conn.execute("DELETE FROM users")
        await conn.execute("DELETE FROM nas_logins")
        # Create a profile manually since we bypassed routine
        await conn.execute("""
            INSERT INTO users (profileid, userid, console)
            VALUES (10001, 'user-xyz', 1)
        """)
        # Insert NAS payload
        await conn.execute("""
            INSERT INTO nas_logins (userid, authtoken, data)
            VALUES ('user-xyz', 'tok', '{"ingamesn": "PILOT-SUCCESS"}')
        """)
    await db.close()

def run_verification():
    print("--- COMMENCING PILOT VERIFICATION LOOP ---")
    
    # 1. Prepare DB
    asyncio.run(setup_test_data())
    print("[1] Test Data Injected into PostgreSQL.")
    
    # 2. Instantiate the QR Server
    qr = GameSpyQRServer()
    
    # Mirror absolute production topology: persistent singleton loop
    qr._db_loop = asyncio.new_event_loop()
    qr.db = PostgresGamespyDatabase("postgresql://dwc_admin:insecure_dev_password@localhost:5432/gamespy")
    
    # Utilize that persistent loop for everything
    qr._db_loop.run_until_complete(qr.db.initialize_database())
    
    print("[2] Attempting simulated execution call...")
    
    # Simulate the EXACT nested logic of QRServer from line 361
    try:
        profile = qr._sync_db_call(qr.db.get_profile_from_profileid(10001))
        print(f"[3] Profile Retrieved: {profile['userid']}")
        
        naslogin = qr._sync_db_call(qr.db.get_nas_login_from_userid(profile['userid']))
        print(f"[4] NAS Login Retrieved! InGameSN: {naslogin['ingamesn']}")
        
        assert naslogin['ingamesn'] == "PILOT-SUCCESS"
        print("\n🏆 ABSOLUTE PILOT VICTORY ACHIEVED 🏆")
    except Exception as e:
        print(f"\n❌ FAILURE: {e}")
        import sys
        sys.exit(1)
    finally:
        qr._db_loop.run_until_complete(qr.db.close())
        qr._db_loop.close()

if __name__ == "__main__":
    run_verification()
