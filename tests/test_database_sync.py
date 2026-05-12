import pytest
import os
import sys

# Ensure local module discovery
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gamespy.pg_database_sync import PostgresGamespyDatabaseSync

@pytest.fixture(scope="module")
def sync_db():
    """Prepares a persistent authenticated test singleton of our magic sync proxy."""
    # Use standard authenticated dev DSN used across all our test suites
    dsn = "postgresql://dwc_admin:insecure_dev_password@localhost:5432/gamespy"
    bridge = PostgresGamespyDatabaseSync(dsn)
    
    yield bridge
    
    # Force graceful termination loop release
    bridge.close()

def test_sync_magic_method_forwarding(sync_db):
    """
    Validates our magical dynamic reflection capability correctly captures ANY async method
    and presents it transparently to standard synchronous calls without configuration.
    """
    # 1. Test a fundamental read that returns data immediately via sync invoke
    # ProfileID 1 should normally be absent or present, but shouldn't throw exception.
    profile = sync_db.get_profile_from_profileid(9999999)
    
    # Result might be None, which is fine, it confirms execution successfully cycled through
    # the backend and returned data gracefully across the bridge thread!
    assert profile is None or isinstance(profile, dict)

def test_sync_direct_dispatch_capability(sync_db):
    """Ensures direct generalized dispatcher executions operate natively."""
    
    async def dummy_coro():
        return "SUCCESS_DISPATCH"
        
    # Submit directly to the underlying async loop
    result = sync_db._call(dummy_coro())
    
    assert result == "SUCCESS_DISPATCH"

def test_sync_atomic_operation_lifecycle(sync_db):
    """Executes definitive read/write lifecycle entirely through synchronous magic routing."""
    
    # Trigger an insert transparently!
    sync_db.pd_insert(88888, "test_idx", "test_type", "MAGIC_DATA_PAYLOAD")
    
    # Immediately retrieve it transparently!
    row = sync_db.pd_get(88888, "test_idx", "test_type")
    
    assert row is not None
    assert row['data'] == "MAGIC_DATA_PAYLOAD"
