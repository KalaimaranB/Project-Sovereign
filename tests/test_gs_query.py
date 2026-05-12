import pytest
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gamespy import gs_query

def test_parse_gamespy_message_basic():
    """Tests robust characterization of gamespy message slicing."""
    msg = "\\login\\1\\user\\bob\\final\\"
    # In python 2, strings were essentially bytes. We pass it as a normal string now.
    stack, remainder = gs_query.parse_gamespy_message(msg)
    
    assert len(stack) == 1
    assert stack[0]["__cmd__"] == "login"
    assert stack[0]["user"] == "bob"
    assert remainder == ""

def test_parse_gamespy_message_partial():
    """Verify remaining buffers are tracked correctly for async accumulation."""
    msg = "\\login\\1\\user\\bob\\final\\\\nextcom"
    stack, remainder = gs_query.parse_gamespy_message(msg)
    assert len(stack) == 1
    assert remainder == "\\nextcom"

def test_create_gamespy_message():
    """Verify output creation exact match."""
    d = [
        ("__cmd__", "lc"),
        ("__cmd_val__", "1"),
        ("challenge", "ABCDEF")
    ]
    out = gs_query.create_gamespy_message(d)
    assert out == "\\lc\\1\\challenge\\ABCDEF\\final\\"

def test_parse_gamespy_message_raw_bytes():
    """This is what incoming TCP data looks like (bytes). Should parse properly."""
    raw = b"\\login\\1\\final\\"
    stack, remainder = gs_query.parse_gamespy_message(raw)
    assert len(stack) == 1, "Should successfully parse one message"
    assert stack[0]["__cmd__"] == "login"
