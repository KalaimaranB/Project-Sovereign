import pytest
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gamespy import gs_utility

def test_rc4_encrypt():
    """Test the core obfuscation encryption module."""
    key = b"testkey"
    data = b"helloworld"
    
    encrypted = gs_utility.rc4_encrypt(key, data)
    assert len(encrypted) == len(data)
    assert encrypted != data
    
    # S-Box has mutated the static mutable list(range(0x100)) successfully without crashing now

def test_base64_custom_variants():
    """Verifies GameSpy base64 bracket style string encoding."""
    inp = b"somedata"
    enc = gs_utility.base64_encode(inp)
    assert b'+' not in enc
    assert b'/' not in enc
    
    dec = gs_utility.base64_decode(enc)
    assert dec == inp

def test_crypto_hashes():
    """Confirm MD5 concatenation loops accept bytes/strings smoothly."""
    chall = "AB12"
    ac_chall = "CD34"
    key = "SECKEY"
    tok = "AUTHTOKEN"
    
    resp = gs_utility.generate_response(chall, ac_chall, key, tok)
    assert isinstance(resp, str)
    assert len(resp) == 32 # valid hex md5
