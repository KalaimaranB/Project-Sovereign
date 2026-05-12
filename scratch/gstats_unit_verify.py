import asyncio
from gamespy_gamestats_server import Gamestats
from gamespy.pg_database import PostgresGamespyDatabase
import sys

class MockTransport:
    def write(self, data): pass

def run():
    print("--- COMMENCING FINAL GSTATS UNIT LOGIC VERIFICATION ---")
    
    # 1. Clean Database Environment
    async def clean():
        db = PostgresGamespyDatabase("postgresql://dwc_admin:insecure_dev_password@localhost:5432/gamespy")
        await db.initialize_database()
        async with db.pool.acquire() as conn:
            await conn.execute("DELETE FROM gamestat_profile")
        await db.close()
    asyncio.run(clean())
    print("[1] Clean test state primed.")
    
    # 2. Instantiate Target Twisted Protocol Controller
    # The protocol expects sessions dictionary and address object in init.
    class MockAddr: host = '127.0.0.1'; port = 12345
    
    print("[2] Booting Gamestats Protocol instance (spawning universal bridge)...")
    protocol = Gamestats({}, MockAddr())
    protocol.transport = MockTransport()
    
    # Setup state preconditions normally handled during auth chain
    protocol.profileid = 99999
    protocol.lid = "1"
    protocol.data = "\\data\\my_stats_blob\\final\\" # Emulate incoming packet store
    
    # 3. Trigger high-stakes SET DATA handler execution!
    parsed_payload = {
        '__cmd__': 'setpd',
        'pid': '99999',
        'dindex': '0',
        'ptype': 'global',
        'length': '13' # Length of "my_stats_blob"
    }
    
    print("[3] Executing perform_setpd direct logic injection...")
    try:
        # Trigger the actual production server code, passing thru our magic proxy!
        protocol.perform_setpd(parsed_payload)
        print("Logic completed without exception!")
    except Exception as e:
        print(f"\n❌ ERROR IN SERVER LOGIC: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    # 4. Final Verification from physical disk!
    async def check():
        db2 = PostgresGamespyDatabase("postgresql://dwc_admin:insecure_dev_password@localhost:5432/gamespy")
        await db2.initialize_database()
        row = await db2.pd_get(99999, '0', 'global')
        await db2.close()
        return row
        
    final_row = asyncio.run(check())
    print(f"\n[4] EXTRACTED ROW FROM POSTGRES: {final_row}")
    
    if final_row is not None and final_row['data'] == 'my_stats_blob':
        print("\n🏆 TARGET #3 - TELEMETRY TRIUMPH ACHIEVED 🏆")
    else:
        print("\n❌ FAILURE: Blob failed to persist correctly!")
        sys.exit(1)
    
    # Shutdown cleanup
    protocol.db.close()

if __name__ == "__main__":
    run()
