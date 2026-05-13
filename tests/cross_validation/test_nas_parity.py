import pytest
import requests
import threading
import time
from services.nas_server import NasServer

from tests.cross_validation.reference_runner import ReferenceEmulator
import dwc_config

from unittest.mock import patch

@pytest.fixture(scope="module")
def servers():
    # Setup our Modern Server on Port 19003 to avoid conflicts with docker-compose
    patcher = patch('dwc_config.get_ip_port', return_value=('127.0.0.1', 19003))
    patcher.start()
    
    nas = NasServer()
    server_thread = threading.Thread(target=nas.start, daemon=True)
    server_thread.start()
    
    # Wait for modern server
    time.sleep(1)

    # Setup Original Reference Server on Port 19002 (docker maps 19002 -> 9000 inside container)
    ref = ReferenceEmulator(port_mapping={19002: 9000})
    ref.start()
    
    yield
    
    ref.stop()

def test_nas_login_parity(servers):
    # This is the exact payload captured from the Wii
    payload = {
        b'action': b'login', 
        b'gsbrcd': b'RBWE04c09nh', 
        b'userid': b'0000000000002', 
        b'ingamesn': b'\x00M\x00a\x00r\x00a\x00n', 
        b'sdkver': b'001000', 
        b'gamecd': b'RBWE', 
        b'makercd': b'01', 
        b'unitcd': b'1', 
        b'macadr': b'0017ab729d15', 
        b'lang': b'01', 
        b'devtime': b'260512162302', 
        b'csnum': b'LU205145412', 
        b'cfc': b'1664590732533275', 
        b'region': b'01'
    }

    # Convert payload dictionary to query string bytes as the Wii sends them
    from other.utils import dict_to_qs
    req_body = dict_to_qs(payload)

    # Fire to Modern Server
    resp_modern = requests.post("http://127.0.0.1:19003/ac", data=req_body, headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=5)
    
    # Fire to Reference Server
    resp_ref = requests.post("http://127.0.0.1:19002/ac", data=req_body, headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=5)

    assert resp_modern.status_code == resp_ref.status_code
    assert resp_modern.headers.get("NODE") == resp_ref.headers.get("NODE")
    
    # We parse the responses to dicts to compare them without worrying about key ordering
    from other.utils import qs_to_dict
    mod_dict = qs_to_dict(resp_modern.content)
    ref_dict = qs_to_dict(resp_ref.content)
    
    # Both should have returncd = 001 (or whatever logic matches)
    assert mod_dict.get('returncd') == ref_dict.get('returncd')
    assert b'token' in mod_dict
    assert b'token' in ref_dict
