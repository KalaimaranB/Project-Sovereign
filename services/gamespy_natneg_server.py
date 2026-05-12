"""DWC Network Server Emulator - Modernized NatNeg Server

    Refactored utilizing Python 3.13 asyncio native non-blocking architectures,
    removing legacy SocketServer thread pools.
"""

import asyncio
import logging
import sys
import os
from other import metrics
from gamespy_backend_server import GameSpyBackendServer


import dwc_config
import other.utils as utils
from gamespy.natneg_protocol import NatNegProtocol

logger = dwc_config.get_logger('GameSpyNatNegServer')



class ServerDataProxyResolver:
    """
    Safely encapsulates cross-process synchronization manager connection
    for transparent lookups without exposing interprocess mechanisms to protocols.
    """
    def __init__(self):
        self.backend = GameSpyBackendServer()
        
    def connect(self):
        logger.info("Native Backend library resolved successfully.")

    def __call__(self, gameid, session_id, client_id, sessions):
        """Direct resolution lookup hook passed into NatNegProtocol."""
        # Logic ported straight from legacy get_server_addr logic
        try:
            client_info = sessions[session_id][client_id]
            ip_str = client_info['addr'][0]
            
            # Primary lookup via public IP
            proxy_servers = self.backend.get_natneg_server(session_id)
            if proxy_servers:
                 for console_mode in [False, True]:
                     ip_val = str(utils.get_ip_from_str(ip_str, console_mode))
                     match = next((s for s in proxy_servers if s.get('publicip') == ip_val), None)
                     if match:
                         return match
            
            # Fallback lookup via local address
            for console_mode in [False, True]:
                ip_val = str(utils.get_ip_from_str(ip_str, console_mode))
                alt_match = self.backend.find_server_by_local_address(
                    ip_val, client_info['localaddr'], client_info['gameid']
                )
                if alt_match:
                    return alt_match
                    
        except Exception:
            logger.error("Proxy query failure: %s", sys.exc_info()[1])
            
        return None

class NatNegAsyncProtocol(asyncio.DatagramProtocol):
    """
    High performance AsyncIO edge adapter connecting raw sockets to native logic.
    """
    def __init__(self, resolver):
        # Initialize the validated core logic layer inside the shell
        self.logic = NatNegProtocol(server_data_resolver=resolver)
        self.transport = None
        
    def connection_made(self, transport):
        self.transport = transport
        logger.info("Datagram endpoint ready.")
        
    def datagram_received(self, data, addr):
        # Detect Sovereign Transparent Header Encapsulation (STHE) from trusted WAF boundary
        import os
        is_loopback = addr[0] in ('127.0.0.1', '::1')
        is_trusted = is_loopback or os.environ.get('TRUST_ALL_PROXIES') == '1'
        
        using_proxy = False
        effective_client_addr = addr
        
        if is_trusted and data.startswith(b'SOV\x01') and len(data) >= 10:
            import struct
            try:
                # Header: SOV\x01 (4) + IP (4) + Port (2)
                ip_bytes = data[4:8]
                port_bytes = data[8:10]
                ip = '.'.join(str(b) for b in ip_bytes)
                port = struct.unpack("!H", port_bytes)[0]
                
                effective_client_addr = (ip, port)
                data = data[10:]
                using_proxy = True
            except Exception:
                logger.error("Failed parsing SOV header wrapper from %s", addr)

        # Immediate evaluation utilizing robust parsed routing
        effects = self.logic.handle_packet(data, effective_client_addr)
        
        # Execute yielded transport events instantly
        for effect in effects:
            if using_proxy:
                import struct
                try:
                    # Re-wrap the egress vector targeting the specific client
                    dest_ip = bytearray(int(x) for x in effect.addr[0].split('.'))
                    dest_port = struct.pack("!H", effect.addr[1])
                    wrapped = b'SOV\x01' + bytes(dest_ip) + dest_port + effect.data
                    
                    # Forward back through the C proxy listener loopback
                    self.transport.sendto(wrapped, addr)
                except Exception:
                    logger.error("Failed to wrap SOV response header for client %s", effect.addr)
            else:
                # Direct legacy direct-connected logic
                self.transport.sendto(effect.data, effect.addr)
            
    def error_received(self, exc):
        logger.error("NatNeg socket error encountered: %s", exc)

async def main():
    # Launch centralized telemetry scraper endpoint
    metrics_port = int(os.environ.get('METRICS_PORT', 9101))
    metrics.launch_metrics_endpoint(metrics_port)

    ip, port = dwc_config.get_ip_port('GameSpyNatNegServer')
    logger.info("Initializing Modern Async NatNeg Server on %s:%d", ip, port)
    
    # Bootstrap connection sharing manager backend
    resolver = ServerDataProxyResolver()
    resolver.connect()
    
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: NatNegAsyncProtocol(resolver),
        local_addr=(ip, port)
    )
    
    logger.info("Async Event Loop active and monitoring for incoming packets.")
    try:
        # Sleep forever serving
        await asyncio.Future() 
    finally:
        transport.close()

class GameSpyNatNegServer(object):
    """Legacy class shim to preserve master_server start() contract."""
    def start(self):
        # Starts Async engine
        asyncio.run(main())

if __name__ == "__main__":
    # Manual launcher trigger
    srv = GameSpyNatNegServer()
    srv.start()
