import socket
import subprocess
import time
import pytest
import struct
import os

@pytest.fixture
def compiled_proxy():
    """Ensures the C daemon is compiled and returns its absolute executable path."""
    proxy_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dpi_proxy"))
    # Invoke standard GNU make in the targeted workspace
    subprocess.run(["make", "all"], cwd=proxy_dir, check=True, stdout=subprocess.PIPE)
    return os.path.join(proxy_dir, "sovereign_dpi_proxy")

def get_free_port():
    """Allocates an available ephemeral UDP port dynamically to isolate testing threads."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def test_proxy_natneg_integration(compiled_proxy):
    """
    Validates end-to-end NatNeg packet drop/relay vectors through the C binary:
    1. Dropping malformed magic buffers.
    2. Injecting the STHE header upon valid packets.
    3. Transparently stripping STHE headers upon backend egress flows.
    """
    pub_port = get_free_port()
    back_port = get_free_port()

    # Spawn security perimeter daemon in subprocess
    cmd = [compiled_proxy, str(pub_port), "127.0.0.1", str(back_port), "natneg"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(0.2) # Brief grace interval allowing Unix select loops to bind

    back_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    back_sock.bind(('127.0.0.1', back_port))
    back_sock.settimeout(0.5)
    client_sock.settimeout(0.5)

    try:
        # VECTOR A: Invalid Packet (Malformed Magic) -> Assert DROP
        bad_pkt = b"\xAA\xBB\xCC\xDD\xEE\xFF\x00\x00"
        client_sock.sendto(bad_pkt, ('127.0.0.1', pub_port))

        with pytest.raises(socket.timeout):
            # The Backend must receive absolutely nothing.
            back_sock.recvfrom(1024)

        # VECTOR B: Valid Init Packet -> Assert Forward + Header Injection
        # Magic (6) + Padding (1) + Opcode (1) + Extra (2)
        valid_pkt = b"\xFD\xFC\x1E\x66\x6A\xB2\x00\x05\x11\x22"
        client_sock.sendto(valid_pkt, ('127.0.0.1', pub_port))

        payload, proxy_addr = back_sock.recvfrom(1024)
        
        # Assert SOV Framing matches expectation
        assert payload.startswith(b"SOV\x01"), "Proxy must prepend the Sovereign Magic tag"
        assert len(payload) == 10 + len(valid_pkt), "Full STHE encapsulation size check"
        
        # Verify embedded client port matches the source socket
        client_actual_port = client_sock.getsockname()[1]
        embedded_port = struct.unpack("!H", payload[8:10])[0]
        assert embedded_port == client_actual_port, "STHE must preserve original client source port"

        # Verify original payload extraction
        assert payload[10:] == valid_pkt, "Original datagram must arrive unmodified"

        # VECTOR C: Backend Response -> Assert Header Strip + Outbound Dispatch
        resp_raw = b"\xFE\xFD\x09\xAA\xBB\xCC\xDD" # Dummy gamespy responses
        client_ip_bytes = payload[4:8]
        resp_wrapped = b"SOV\x01" + client_ip_bytes + struct.pack("!H", client_actual_port) + resp_raw
        
        # Send wrapped packet back to proxy
        back_sock.sendto(resp_wrapped, proxy_addr)

        # Assert Client receives clean un-wrapped packet
        client_payload, client_recv_addr = client_sock.recvfrom(1024)
        assert client_payload == resp_raw, "Proxy must strip the header before delivery to console"
        assert client_recv_addr[1] == pub_port, "Packet source port must match the public gateway"

    finally:
        proc.terminate()
        proc.wait()
        back_sock.close()
        client_sock.close()

def test_proxy_qr_integration(compiled_proxy):
    """
    Validates QR printable ASCII key-value Heartbeat verification rules.
    1. Dropping key-value blobs missing null delimiters.
    2. Passing clean key-value buffers seamlessly.
    """
    pub_port = get_free_port()
    back_port = get_free_port()

    cmd = [compiled_proxy, str(pub_port), "127.0.0.1", str(back_port), "qr"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(0.2)

    back_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    back_sock.bind(('127.0.0.1', back_port))
    back_sock.settimeout(0.5)
    client_sock.settimeout(0.5)

    try:
        # VECTOR A: Heartbeat missing Null bytes (Abuse Probe) -> Assert DROP
        bad_heartbeat = b"\x03\x00\x00\x00\x00" + b"InfiniteDataStreamOverflowWithoutTerminations"
        client_sock.sendto(bad_heartbeat, ('127.0.0.1', pub_port))

        with pytest.raises(socket.timeout):
            back_sock.recvfrom(1024)

        # VECTOR B: Valid Heartbeat -> Assert Forward + Header Injection
        good_heartbeat = b"\x03\x01\x02\x03\x04" + b"gamename\x00mariokart\x00"
        client_sock.sendto(good_heartbeat, ('127.0.0.1', pub_port))

        payload, proxy_addr = back_sock.recvfrom(1024)
        assert payload.startswith(b"SOV\x01")
        assert payload[10:] == good_heartbeat

    finally:
        proc.terminate()
        proc.wait()
        back_sock.close()
        client_sock.close()
