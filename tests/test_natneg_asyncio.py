import pytest
import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gamespy.natneg_protocol import NatNegProtocol

class MockTransport:
    def __init__(self):
        self.sent_packets = []
        
    def sendto(self, data, addr):
        self.sent_packets.append((data, addr))
        
    def close(self):
        pass

# This describes our forthcoming Asyncio wrapper around the logic controller
class NatNegAsyncProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.logic = NatNegProtocol()
        self.transport = None
        
    def connection_made(self, transport):
        self.transport = transport
        
    def datagram_received(self, data, addr):
        effects = self.logic.handle_packet(data, addr)
        for effect in effects:
             # This is non-blocking and uses pure asyncio event loops!
             self.transport.sendto(effect.data, effect.addr)

@pytest.mark.asyncio
async def test_async_integration_wiring():
    """End to end internal validation that transport logic loops connect."""
    transport = MockTransport()
    proto = NatNegAsyncProtocol()
    proto.connection_made(transport)
    
    # Trigger an internal packet
    input_data = bytes.fromhex("fdfc1e666ab2030a0000000001000000000000000000") # Address Check hex approx
    proto.datagram_received(input_data, ("127.0.0.1", 5555))
    
    assert len(transport.sent_packets) >= 1
    out_data, out_addr = transport.sent_packets[0]
    assert out_addr == ("127.0.0.1", 5555)
    assert out_data[7] == 0x0B # Check successfully yielded address reply
