import pytest
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# TDD: We declare intent to use a standalone protocol handler.
# This DOES NOT exist yet, fitting Red phase.
try:
    from gamespy.natneg_protocol import NatNegProtocol
except ImportError:
    NatNegProtocol = None

def test_natneg_protocol_import():
    assert NatNegProtocol is not None, "NatNegProtocol class should exist for logic decoupling"

def test_natneg_init_decoding():
    """Capture logic flow for initializing command."""
    if NatNegProtocol is None:
        pytest.skip("NatNegProtocol does not exist yet")
        
    # Raw setup byte sequence extracted from source documentation for Mario Kart Wii Init
    init_bytes = bytes.fromhex("fdfc1e666ab203003df100710000010a0001e200006d6172696f6b61727477696900")
    client_addr = ("192.168.1.100", 12345)
    
    # We imagine our pure logic doesn't require socket threading queues but collects "Effects"
    # That can be processed by any IO system (asyncio OR socketserver).
    protocol = NatNegProtocol()
    effects = protocol.handle_packet(init_bytes, client_addr)
    
    # Verify output bytes are computed correctly byte-for-byte according to spec
    # Expected response: original 14 bytes mutated at index 7 and appended with specific marker
    # Marker was: 0xff, 0xff, 0x6d, 0x16, 0xb5, 0x7d, 0xea
    assert len(effects) >= 1, "Must generate at least one network response response"
    
    response_effect = effects[0]
    assert response_effect.addr == client_addr
    resp_data = bytearray(response_effect.data)
    assert resp_data[7] == 0x01 # INITACK opcode
    assert resp_data[-7:] == bytearray([0xff, 0xff, 0x6d, 0x16, 0xb5, 0x7d, 0xea])
    
    # Verify session was stored internally
    session_id = 0x3df10071 # Derived from index 8 of init_bytes (bigEndian)
    # Wait source code says littleEndian? `utils.get_int(recv_data, 8)`. utils default is LE.
    # Let's check later.
