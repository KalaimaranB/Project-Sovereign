import pytest
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gamespy.profile_protocol import ProfileProtocol

def test_profile_protocol_init():
    """Validate initial handshake string is queued immediately on setup."""
        
    # Mock a database interface to follow SOLID injection pattern
    class MockDB:
        pass
        
    # Protocol will instantiate
    proto = ProfileProtocol(db=MockDB(), address=("127.0.0.1", 1234))
    
    # Step 1: Upon construction, does it generate the initial \lc\ Challenge sequence?
    effects = proto.on_connection_made()
    assert len(effects) >= 1
    
    handshake_raw = effects[0].data
    assert b"\\lc\\" in handshake_raw
    assert b"\\challenge\\" in handshake_raw
