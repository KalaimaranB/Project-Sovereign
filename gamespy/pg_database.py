import asyncpg
import logging
import hashlib
import time
import other.utils as utils

try:
    from gamespy.i_gs_database import IGamespyDatabase
except ImportError:
    # Secures robustness for local-scope interactive debug sessions
    from i_gs_database import IGamespyDatabase

logger = logging.getLogger('PostgresDatabase')

class PostgresGamespyDatabase(IGamespyDatabase):
    """
    Modern, thread-safe async PostgreSQL engine fulfillment of the IGamespyDatabase contract.
    Specifically designed for non-blocking event loop native database throughput.
    """
    def __init__(self, dsn=None):
        import os
        # Prioritize explicit injection -> then ENV -> then hardcoded local fallback
        self.dsn = dsn or os.environ.get("DATABASE_URL") or "postgresql://dwc_admin:insecure_dev_password@localhost:5432/gamespy"
        self.pool = None

    async def initialize_database(self):
        """Establishes native postgres connection pool and seeds schemas."""
        self.pool = await asyncpg.create_pool(self.dsn)
        
        async with self.pool.acquire() as conn:
            # Convert BLOB to BYTEA, apply proper typing adjustments
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    profileid SERIAL PRIMARY KEY, 
                    userid TEXT, 
                    password TEXT, 
                    gsbrcd TEXT, 
                    email TEXT, 
                    uniquenick TEXT, 
                    pid TEXT, 
                    lon TEXT, 
                    lat TEXT, 
                    loc TEXT, 
                    firstname TEXT, 
                    lastname TEXT, 
                    stat TEXT, 
                    partnerid TEXT, 
                    console INT, 
                    csnum TEXT, 
                    cfc TEXT, 
                    bssid TEXT, 
                    devname BYTEA, 
                    birth TEXT, 
                    gameid TEXT, 
                    enabled INT, 
                    zipcode TEXT, 
                    aim TEXT
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session TEXT PRIMARY KEY, 
                    profileid INT, 
                    loginticket TEXT
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS buddies (
                    userProfileId INT, 
                    buddyProfileId INT, 
                    time INT, 
                    status INT, 
                    notified INT, 
                    gameid TEXT, 
                    blocked INT
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pending_messages (
                    sourceid INT, 
                    targetid INT, 
                    msg TEXT
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS nas_logins (
                    userid TEXT, 
                    authtoken TEXT, 
                    data TEXT
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS banned (
                    gameid TEXT, 
                    ipaddr TEXT
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pending (macadr TEXT)
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS registered (macadr TEXT)
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS gamestat_profile (
                    profileid INT, 
                    dindex TEXT, 
                    ptype TEXT, 
                    data TEXT,
                    UNIQUE(profileid, dindex, ptype)
                )
            """)
            
            # Ensure legacy performance indexes exist in native PG
            await conn.execute("CREATE INDEX IF NOT EXISTS users_userid_idx ON users(userid)")
            await conn.execute("CREATE INDEX IF NOT EXISTS buddies_userProfileId_idx ON buddies(userProfileId)")
            await conn.execute("CREATE INDEX IF NOT EXISTS buddies_buddyProfileId_idx ON buddies(buddyProfileId)")

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def check_user_exists(self, userid, gsbrcd):
        async with self.pool.acquire() as conn:
            val = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE userid = $1 AND gsbrcd = $2",
                str(userid), gsbrcd
            )
            return val > 0

    async def create_user(self, userid, password, email, uniquenick, gsbrcd,
                           console, csnum, cfc, bssid, devname, birth, gameid, macadr):
        
        # Maintain existing password hashing logic integrity
        md5 = hashlib.md5()
        md5.update(password.encode('latin-1') if isinstance(password, str) else password)
        pw_hash = md5.hexdigest()
        
        async with self.pool.acquire() as conn:
            # We leverage Postgres SERIAL by omitting profileid and using RETURNING to guarantee atomicity
            profileid = await conn.fetchval("""
                INSERT INTO users (
                    userid, password, gsbrcd, email, uniquenick, 
                    pid, lon, lat, loc, firstname, lastname, stat, partnerid, enabled, zipcode, aim,
                    console, csnum, cfc, bssid, devname, birth, gameid
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16,
                    $17, $18, $19, $20, $21, $22, $23
                ) RETURNING profileid
            """, 
            str(userid), pw_hash, gsbrcd, email, uniquenick,
            "11", "0.000000", "0.000000", "", "", "", "", "", 1, "", "",
            console, csnum, cfc, bssid, devname, birth, gameid
            )
            return profileid

    async def perform_login(self, userid, password, gsbrcd):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT profileid, enabled, gsbrcd FROM users WHERE userid = $1 AND gsbrcd = $2",
                str(userid), gsbrcd
            )
            if row and row['enabled'] == 1 and row['gsbrcd'] == gsbrcd:
                return row['profileid']
        return None

    async def check_user_enabled(self, userid, gsbrcd):
        async with self.pool.acquire() as conn:
            val = await conn.fetchval(
                "SELECT enabled FROM users WHERE userid = $1 AND gsbrcd = $2",
                str(userid), gsbrcd
            )
            return val == 1

    async def check_profile_exists(self, profileid):
        async with self.pool.acquire() as conn:
            val = await conn.fetchval("SELECT COUNT(*) FROM users WHERE profileid = $1", profileid)
            return val > 0

    async def get_profile_from_profileid(self, profileid):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE profileid = $1",
                int(profileid)
            )
            return dict(row) if row else None

    async def get_nas_login_from_userid(self, userid):
        """Retrieves active login struct associated with user identifier."""
        import json
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data FROM nas_logins WHERE userid = $1",
                str(userid)
            )
            if not row:
                return None
            try:
                return json.loads(row['data'])
            except Exception:
                return None

    # Contract fulfillment for remaining stubbed interfaces
    async def get_nas_login(self, authtoken):
        import json
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data FROM nas_logins WHERE authtoken = $1",
                str(authtoken)
            )
            return json.loads(row['data']) if row else None

    async def pd_insert(self, profileid, dindex, ptype, data):
        """
        High-performance atomic merge utility locking telemetry state safely.
        Leverages native Postgres ON CONFLICT semantics eliminating race-conditions.
        """
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO gamestat_profile (profileid, dindex, ptype, data)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (profileid, dindex, ptype)
                DO UPDATE SET data = EXCLUDED.data
            """, int(profileid), str(dindex), str(ptype), str(data))

    async def pd_get(self, profileid, dindex, ptype):
        """Direct low-latency blob retrieval extracting specific telemetry datasets."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM gamestat_profile
                WHERE profileid = $1 AND dindex = $2 AND ptype = $3
            """, int(profileid), str(dindex), str(ptype))
            
            return dict(row) if row else None

    async def is_banned(self, postdata):
        """Identifies prohibited system accesses anchoring ban registry."""
        async with self.pool.acquire() as conn:
            val = await conn.fetchval(
                "SELECT COUNT(*) FROM banned WHERE gameid = $1 AND ipaddr = $2",
                postdata['gamecd'][:-1], postdata['ipaddr']
            )
            return int(val) > 0

    async def get_next_available_userid(self):
        """Dynamic incremental ID provisioner generating padded console token IDs."""
        async with self.pool.acquire() as conn:
            max_user = await conn.fetchval("SELECT max(userid) FROM users")
            
        if max_user is None:
            # Legacy fallback establishing baseline user 2
            return '0000000000002'
        else:
            try:
                numeric = int(max_user) + 1
                return f"{numeric:013d}"
            except ValueError:
                # Emergency baseline recovery
                return '0000000000002'

    async def generate_authtoken(self, userid, data):
        """Generating collision-free randomized authentication tokens."""
        import json
        
        # Safe local imports avoiding implicit recursion cycles
        try:
            import gamespy.gs_utility as gs_utils
        except ImportError:
            import gs_utility as gs_utils
            
        size = 80
        authtoken = ""
        
        async with self.pool.acquire() as conn:
            # 1. Unique token generation loop
            while True:
                authtoken = "NDS" + utils.generate_random_str(size)
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM nas_logins WHERE authtoken = $1",
                    authtoken
                )
                if not count:
                    break
            
            # 2. Preparation of serialized payload
            # Maintain encoding parity for embedded fields if present
            if "devname" in data:
                data["devname"] = gs_utils.base64_encode(data["devname"])
            if "ingamesn" in data:
                data["ingamesn"] = gs_utils.base64_encode(data["ingamesn"])
            
            serialized = json.dumps(data)
            
            # 3. Check for existing user row enabling atomic merge-update
            exists = await conn.fetchrow("SELECT userid FROM nas_logins WHERE userid = $1", str(userid))
            
            if not exists:
                await conn.execute(
                    "INSERT INTO nas_logins (userid, authtoken, data) VALUES ($1, $2, $3)",
                    str(userid), authtoken, serialized
                )
            else:
                await conn.execute(
                    "UPDATE nas_logins SET authtoken = $1, data = $2 WHERE userid = $3",
                    authtoken, serialized, str(userid)
                )
                
        return authtoken

    async def update_profile(self, profileid, field_dict):
        """
        Optimized bulk update fulfillment implementing previously identified legacy TODO.
        Safely whitelist merges dictionary values directly to corresponding SQL column names.
        """
        # Restrict modification only to explicitly known persistent column identities
        safe_columns = {
            'firstname', 'lastname', 'email', 'uniquenick', 
            'lon', 'lat', 'loc', 'zipcode', 'aim', 'birth'
        }
        updates = {k: v for k, v in field_dict.items() if k.lower() in safe_columns}
        
        if not updates:
            return
            
        async with self.pool.acquire() as conn:
            # Build dynamic SET clause string for asyncpg parameter injection safety
            set_pairs = []
            params = []
            for i, (k, v) in enumerate(updates.items()):
                set_pairs.append(f"\"{k}\" = ${i+1}")
                params.append(str(v))
            
            # Append profileid as absolute tail parameter
            params.append(profileid)
            query = f"UPDATE users SET {', '.join(set_pairs)} WHERE profileid = ${len(params)}"
            
            await conn.execute(query, *params)

    async def get_next_free_profileid(self):
        # Technically redundant under PostgreSQL SERIAL mechanism but preserved for backward simulation
        async with self.pool.acquire() as conn:
            val = await conn.fetchval("SELECT MAX(profileid) FROM users")
            return (val or 0) + 1

    # --- Session Management Implementations ---

    async def _generate_session_key(self, conn):
        """Generates unique random token string validating non-collision against active pools."""
        while True:
            candidate = utils.generate_random_number_str(8)
            exists = await conn.fetchval("SELECT COUNT(*) FROM sessions WHERE session = $1", candidate)
            if not exists:
                return candidate

    async def create_session(self, profileid, loginticket):
        async with self.pool.acquire() as conn:
            # Check and cleanse previously existing persistence
            await conn.execute("DELETE FROM sessions WHERE profileid = $1", profileid)
            
            new_key = await self._generate_session_key(conn)
            await conn.execute(
                "INSERT INTO sessions (session, profileid, loginticket) VALUES ($1, $2, $3)",
                new_key, profileid, loginticket
            )
            return new_key

    async def get_profileid_from_session_key(self, session_key):
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT profileid FROM sessions WHERE session = $1", session_key)

    async def get_profile_from_session_key(self, session_key):
        async with self.pool.acquire() as conn:
            pid = await conn.fetchval("SELECT profileid FROM sessions WHERE session = $1", session_key)
            if not pid:
                return None
            row = await conn.fetchrow("SELECT * FROM users WHERE profileid = $1", pid)
            return dict(row) if row else None

    async def delete_session(self, profileid):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM sessions WHERE profileid = $1", profileid)

    # --- Buddy and Inbox Networking Fullfilments ---

    async def add_buddy(self, userProfileId, buddyProfileId):
        now = int(time.time())
        async with self.pool.acquire() as conn:
            # Initial state 0 matches legacy 'Unauthorized' / 'Not blocked' triggers
            await conn.execute(
                "INSERT INTO buddies (userProfileId, buddyProfileId, time, status, notified, gameid, blocked) VALUES ($1, $2, $3, 0, 0, '', 0)",
                userProfileId, buddyProfileId, now
            )

    async def delete_buddy(self, userProfileId, buddyProfileId):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM buddies WHERE userProfileId = $1 AND buddyProfileId = $2",
                userProfileId, buddyProfileId
            )

    async def block_buddy(self, userProfileId, buddyProfileId):
         async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE buddies SET blocked = 1 WHERE userProfileId = $1 AND buddyProfileId = $2",
                userProfileId, buddyProfileId
            )

    async def get_buddy_list(self, userProfileId):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM buddies WHERE userProfileId = $1 AND blocked = 0", userProfileId)
            return [dict(r) for r in rows]

    async def get_blocked_list(self, userProfileId):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM buddies WHERE userProfileId = $1 AND blocked = 1", userProfileId)
            return [dict(r) for r in rows]

    async def save_pending_message(self, sourceid, targetid, msg):
        async with self.pool.acquire() as conn:
            await conn.execute("INSERT INTO pending_messages VALUES ($1, $2, $3)", sourceid, targetid, msg)

    async def get_pending_messages(self, profileid):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM pending_messages WHERE targetid = $1", profileid)
            return [dict(r) for r in rows]

    async def execute_raw(self, query, *args):
        """Direct general execute gateway routing statements directly to the async pool."""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch_raw(self, query, *args):
        """Standard generic retrieval query returning dictionary maps."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(r) for r in rows]

    async def fetchrow_raw(self, query, *args):
        """Retrieve a single dict-mapped row result scalar."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def fetchval_raw(self, query, *args):
        """Fetch scalar raw values direct."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

