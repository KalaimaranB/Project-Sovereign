import pytest
import asyncio
from dnslib import DNSRecord, DNSHeader, DNSQuestion, QTYPE
import socket

# This test will require the server to be running or we can test the handler logic directly.
# Let's test the logic directly to adhere to SOLID principles.

from services.dns_server import DNSHandler, is_target_domain

def test_is_target_domain():
    assert is_target_domain("nas.nintendowifi.net.")
    assert is_target_domain("conntest.nintendowifi.net.")
    assert is_target_domain("gamemaster.gamespy.com.")
    assert not is_target_domain("google.com.")
    assert not is_target_domain("nintendo.com.")

def test_dns_handler_target_domain():
    handler = DNSHandler(target_ip="10.8.0.1")
    
    # Craft a DNS request for a target domain
    q = DNSRecord(q=DNSQuestion("naswii.nintendowifi.net", QTYPE.A))
    
    # Process it
    response_data = handler.process_query(q.pack())
    
    # Parse the response
    response = DNSRecord.parse(response_data)
    
    assert response.header.rcode == 0 # NOERROR
    assert len(response.rr) == 1
    assert str(response.rr[0].rdata) == "10.8.0.1"
    assert response.rr[0].rtype == QTYPE.A

def test_dns_handler_non_target_domain():
    handler = DNSHandler(target_ip="10.8.0.1")
    
    # Craft a DNS request for a non-target domain
    q = DNSRecord(q=DNSQuestion("google.com", QTYPE.A))
    
    # Process it
    response_data = handler.process_query(q.pack())
    
    # Parse the response
    response = DNSRecord.parse(response_data)
    
    # By default, we might just return NXDOMAIN for simplicity in this proxy
    assert response.header.rcode == 3 # NXDOMAIN
    assert len(response.rr) == 0
