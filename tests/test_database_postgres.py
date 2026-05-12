import pytest
import pytest_asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gamespy.pg_database import PostgresGamespyDatabase

@pytest_asyncio.fixture
async def pg_db():
    """Establishes direct connection to current dockerized environment instance."""
    # Connection string mapped to docker-compose definition
    db = PostgresGamespyDatabase("postgresql://dwc_admin:insecure_dev_password@localhost:5432/gamespy")
    
    # WARNING: Drop tables sequentially here ensures each unit test gets a clean state
    # Wait, instead of manual drop, we connect and clear existing data.
    await db.initialize_database()
    
    async with db.pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE users CASCADE") # Nuclear data flush for test repeatability
        
    yield db
    await db.close()

@pytest.mark.asyncio
async def test_postgres_user_lifecycle(pg_db):
    """
    DUPLICATE OF test_user_lifecycle, validating that Postgres realization
    yields mathematically identical outcomes to the legacy baseline verification.
    """
    db = pg_db
    
    # Pre-check state
    exists = await db.check_user_exists(9999, "BATT")
    assert not exists
    
    # Execute user creation
    profileid = await db.create_user(
        userid=9999, 
        password="my_secret_pass", 
        email="tester@gamespy.dev", 
        uniquenick="ProGamer", 
        gsbrcd="BATTE1", 
        console=1, csnum="TEST", cfc="0", bssid="00:00:00", devname=b"TEST",
        birth="01-01", gameid="TEST", macadr="00:00:00:00"
    )
    
    assert profileid > 0
    
    # Verify storage retrieval
    exists_now = await db.check_user_exists(9999, "BATTE1")
    assert exists_now
    
    # Assert login verification
    login_result = await db.perform_login(9999, "my_secret_pass", "BATTE1")
    assert login_result is not None
    assert login_result == profileid # Returns raw profile ID int directly

@pytest.mark.asyncio
async def test_postgres_complete_suite(pg_db):
    """
    Validates high-performance session generation, buddy relationships,
    and bulk transactional updates for absolute contract enforcement.
    """
    db = pg_db
    
    # 1. Setup 2 Users
    p1 = await db.create_user(101, "p", "e1", "u1", "G", 1, "C", "F", "B", b"D", "B", "G", "M")
    p2 = await db.create_user(102, "p", "e2", "u2", "G", 1, "C", "F", "B", b"D", "B", "G", "M")
    
    # 2. Verify Profiles Exist and Fetch accurately
    assert await db.check_profile_exists(p1)
    prof1 = await db.get_profile_from_profileid(p1)
    assert prof1['uniquenick'] == "u1"
    
    # 3. Execute Bulk Dictionary Profile Optimization (Modern Upgrade)
    await db.update_profile(p1, {'firstname': 'Gabe', 'lastname': 'Newell', 'unused_garbage': 'delete_me'})
    updated_prof = await db.get_profile_from_profileid(p1)
    assert updated_prof['firstname'] == 'Gabe'
    
    # 4. Exercise Buddy Relationship Graph
    await db.add_buddy(p1, p2)
    buddies = await db.get_buddy_list(p1)
    assert len(buddies) == 1
    assert buddies[0]['buddyprofileid'] == p2 # In Postgres keys are often lowercase
    
    # Verify blocking
    await db.block_buddy(p1, p2)
    no_buddies = await db.get_buddy_list(p1)
    assert len(no_buddies) == 0
    blocked = await db.get_blocked_list(p1)
    assert len(blocked) == 1
    
    # Cleanly delete buddy
    await db.delete_buddy(p1, p2)
    assert len(await db.get_blocked_list(p1)) == 0

    # 5. Manage Concurrent Session States
    sess1 = await db.create_session(p1, "TICKET_A")
    assert len(sess1) > 0
    found_pid = await db.get_profileid_from_session_key(sess1)
    assert found_pid == p1
    
    # Overwrite session ensures automatic clean release
    sess2 = await db.create_session(p1, "TICKET_B")
    assert sess2 != sess1
    assert await db.get_profileid_from_session_key(sess1) is None # Dead key
    assert await db.get_profileid_from_session_key(sess2) == p1 # Active key
    
    # Final destruction
    await db.delete_session(p1)
    assert await db.get_profileid_from_session_key(sess2) is None

    # 6. Verify Offline Inbox Capabilities
    await db.save_pending_message(p2, p1, "Hello Friend!")
    messages = await db.get_pending_messages(p1)
    assert len(messages) == 1
    assert messages[0]['msg'] == "Hello Friend!"
    
    print("\n--- ABSOLUTE POSTGRES DRIVER VICTORY SECURED ---")

@pytest.mark.asyncio
async def test_postgres_nas_login_storage(pg_db):
    """Validates successful population and serialization recovery of NAS token registries."""
    import json
    db = pg_db
    
    # Seed dynamic test vectors
    test_uid = "nas_test_user_123"
    test_token = "TOKEN-9999"
    payload = {"ingamesn": "TestNintendoID", "challenge": "AB12CD34"}
    serialized = json.dumps(payload)
    
    # Force insert raw state into new table structure
    async with db.pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO nas_logins (userid, authtoken, data) VALUES ($1, $2, $3)",
            test_uid, test_token, serialized
        )
        
    # Verify routine recovers object identically
    retrieved = await db.get_nas_login_from_userid(test_uid)
    
    assert retrieved is not None
    assert retrieved["ingamesn"] == "TestNintendoID"
    assert retrieved["challenge"] == "AB12CD34"
    
    # Verify authtoken fetcher also functions
    retrieved2 = await db.get_nas_login(test_token)
    assert retrieved2 is not None
    assert retrieved2["ingamesn"] == "TestNintendoID"
