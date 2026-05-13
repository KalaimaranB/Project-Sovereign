import asyncio
import logging
import os
import traceback
from dnslib import DNSRecord, QTYPE, RR, A

import dwc_config

logger = dwc_config.get_logger('DNSServer')

TARGET_DOMAINS = [
    "nintendowifi.net",
    "gamespy.com"
]

def is_target_domain(domain: str) -> bool:
    """Check if the requested domain ends with any of the target domains."""
    domain_str = str(domain).lower().rstrip('.')
    for target in TARGET_DOMAINS:
        if domain_str.endswith(target):
            return True
    return False

class DNSHandler:
    def __init__(self, target_ip: str):
        self.target_ip = target_ip

    def process_query(self, data: bytes) -> bytes:
        try:
            request = DNSRecord.parse(data)
            reply = request.reply()
            
            qname = str(request.q.qname)
            qtype = request.q.qtype

            if qtype == QTYPE.A and is_target_domain(qname):
                logger.debug(f"DNS Intercepted: {qname} -> {self.target_ip}")
                reply.add_answer(RR(qname, QTYPE.A, rdata=A(self.target_ip), ttl=60))
            else:
                logger.debug(f"DNS Ignored (NXDOMAIN): {qname}")
                reply.header.rcode = 3  # NXDOMAIN

            return reply.pack()
        except Exception as e:
            logger.error(f"Failed to process DNS query: {e}\n{traceback.format_exc()}")
            return b""

class DNSProtocol(asyncio.DatagramProtocol):
    def __init__(self, target_ip: str):
        self.handler = DNSHandler(target_ip)

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        response_data = self.handler.process_query(data)
        if response_data:
            self.transport.sendto(response_data, addr)

async def main():
    target_ip = os.environ.get("DWC_HOST", "127.0.0.1")
    logger.info(f"Starting DNS Server... routing target domains to {target_ip}")
    
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: DNSProtocol(target_ip),
        local_addr=('0.0.0.0', 53)
    )

    try:
        await asyncio.sleep(3600 * 24 * 365)  # Run forever
    except asyncio.CancelledError:
        pass
    finally:
        transport.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("DNS Server shutting down.")
