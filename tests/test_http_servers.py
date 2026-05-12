import pytest
import io
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import services.nas_server as nas_server
import services.dls1_server as dls1_server

class DummyHeaders(dict):
    def get(self, key, default=None):
        return super().get(key.lower(), default)
    
    def __getitem__(self, key):
        return super().__getitem__(key.lower())

def test_nas_handler_forwarded_ip():
    """TDD test verifying NAS server successfully consumes X-Forwarded-For header behind L7 Gateway."""
    
    # Create base mock for standard server dependencies
    mock_server = MagicMock()
    mock_server.db = MagicMock()
    
    # Instantiate dummy handler properties
    # Note: we don't call __init__ because that starts socket bindings.
    handler = MagicMock(spec=nas_server.NasHTTPServerHandler)
    handler.server = mock_server
    handler.client_address = ('127.0.0.1', 9000) # Simulated Internal ClusterIP
    
    # Configure proxy injected headers
    headers = DummyHeaders()
    headers['content-length'] = '21'
    headers['x-forwarded-for'] = '203.0.113.195' # Standard proxy test IP
    handler.headers = headers
    
    # Simulate proprietary encoded POST body: "action=login&userid=1"
    # Dict to QS uses custom logic, let's simulate a simple post body manually:
    # Base64 "login" is "bG9naW4=" -> replaced "*" is "bG9naW4*"
    # Base64 "1" is "MQ==" -> replaced "*" is "MQ**"
    # Expected: "action=bG9naW4*&userid=MQ**\r\n"
    simulated_body = b"action=bG9naW4*&userid=MQ**\r\n"
    handler.rfile = io.BytesIO(simulated_body)
    
    # Setup routing overrides
    handler.post_paths = nas_server.NasHTTPServerHandler.post_paths
    handler.ac_actions = nas_server.NasHTTPServerHandler.ac_actions
    handler.path = "/ac"
    
    # Track command routing to verify correct IP is passed
    captured_client_address = None
    captured_post_data = None
    
    def mock_handle_ac(inst, addr, post):
        nonlocal captured_client_address, captured_post_data
        captured_client_address = addr
        captured_post_data = post
        return b"OK"
    
    # Inject capture mock inside post path
    handler.post_paths = {"/ac": mock_handle_ac}
    
    # Invoke do_POST using direct unbound method execution to bypass socket binding
    nas_server.NasHTTPServerHandler.do_POST(handler)
    
    # Verify that X-Forwarded-For was picked up correctly
    assert captured_client_address is not None
    assert captured_client_address[0] == '203.0.113.195', "Handler should extract X-Forwarded-For IP over socket IP."
    assert captured_post_data.get('ipaddr') == '203.0.113.195', "IP Address should be accurately embedded inside state dict."

def test_dls1_handler_forwarded_ip():
    """TDD test verifying DLS1 server extracts proxy IP correctly."""
    handler = MagicMock(spec=dls1_server.Dls1HTTPServerHandler)
    handler.client_address = ('10.244.0.12', 8080)
    
    headers = DummyHeaders()
    headers['content-length'] = '21'
    headers['x-forwarded-for'] = '198.51.100.5'
    handler.headers = headers
    
    # Action download contents
    simulated_body = b"action=Y291bnQ*&gamecd=QURBRQ**\r\n"
    handler.rfile = io.BytesIO(simulated_body)
    handler.path = "/download"
    
    captured_addr = None
    def mock_handle_download(inst, addr, post):
        nonlocal captured_addr
        captured_addr = addr
        return b"OK"
        
    handler.post_paths = {"/download": mock_handle_download}
    dls1_server.Dls1HTTPServerHandler.do_POST(handler)
    
    assert captured_addr is not None
    assert captured_addr[0] == '198.51.100.5', "DLS1 must correctly parse X-Forwarded-For behind gateway."

def test_nas_conntest_get():
    """Verifies that direct GET requests return conntest success string."""
    handler = MagicMock(spec=nas_server.NasHTTPServerHandler)
    handler.wfile = io.BytesIO()
    
    nas_server.NasHTTPServerHandler.do_GET(handler)
    
    # Ensure headers were generated
    assert handler.send_response.called
    handler.send_response.assert_any_call(200)
    
    # Ensure exact "ok" response is written
    handler.wfile.seek(0)
    written = handler.wfile.read()
    assert written == b"ok", "GET fallback response must write ok for Nintendo conntest mechanisms."

def test_nas_handler_string_coercion():
    """Verifies NAS server transparently converts string responses to latin-1 bytes."""
    handler = MagicMock(spec=nas_server.NasHTTPServerHandler)
    handler.wfile = io.BytesIO()
    handler.client_address = ('127.0.0.1', 9000)
    
    headers = DummyHeaders()
    headers['content-length'] = '0'
    handler.headers = headers
    handler.rfile = io.BytesIO(b"")
    handler.path = "/ac"
    
    # Mock command to return raw unicode string
    handler.post_paths = {"/ac": lambda inst, addr, post: "response_as_string"}
    
    # Invoke POST - must not raise TypeError!
    nas_server.NasHTTPServerHandler.do_POST(handler)
    
    handler.wfile.seek(0)
    written_data = handler.wfile.read()
    assert written_data == b"response_as_string"

def test_dls1_handler_string_coercion():
    """Verifies DLS1 server transparently converts DLC response lists to latin-1 bytes."""
    handler = MagicMock(spec=dls1_server.Dls1HTTPServerHandler)
    handler.wfile = io.BytesIO()
    handler.client_address = ('127.0.0.1', 8080)
    
    headers = DummyHeaders()
    headers['content-length'] = '0'
    handler.headers = headers
    handler.rfile = io.BytesIO(b"")
    handler.path = "/download"
    
    # Return list mapping as raw str
    handler.post_paths = {"/download": lambda inst, addr, post: "file1.txt\t1024\n"}
    
    # Invoke POST - must not raise TypeError!
    dls1_server.Dls1HTTPServerHandler.do_POST(handler)
    
    handler.wfile.seek(0)
    written_data = handler.wfile.read()
    assert written_data == b"file1.txt\t1024\n"

