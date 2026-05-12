import asyncio
import asyncpg
async def main():
    conn = await asyncpg.connect("postgresql://dwc_admin:insecure_dev_password@localhost:5432/gamespy")
    rows = await conn.fetch("SELECT * FROM nas_logins")
    print(f"FOUND {len(rows)} ROWS:")
    for r in rows:
        print(dict(r))
    await conn.close()
asyncio.run(main())
