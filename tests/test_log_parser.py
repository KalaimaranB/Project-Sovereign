import pytest
import os
import tempfile
from services.patcher_server import parse_logs, get_system_stats

def test_parse_logs():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a fake standard log
        with open(os.path.join(tmpdir, "nas_server.log"), "w") as f:
            f.write("[2026-05-13 12:00:00 | NasServer] Starting up...\n")
            f.write("[2026-05-13 12:00:01 | NasServer] Error: Timeout\n")
        
        # Create a fake tcpdump log
        with open(os.path.join(tmpdir, "tcpdump.log"), "w") as f:
            f.write("1683993600.123456 IP 10.8.0.2.27900 > 10.8.0.1.27900: UDP, length 18\n")
            
        logs = parse_logs(tmpdir)
        
        assert len(logs) == 3
        
        # Check standard logs
        nas_logs = [l for l in logs if l['service'] == 'nas']
        assert len(nas_logs) == 2
        assert nas_logs[0]['level'] == 'error' # The error one might be sorted first depending on timestamp, let's just check existence
        assert any(l['level'] == 'error' and 'Timeout' in l['message'] for l in nas_logs)
        assert any(l['level'] == 'info' and 'Starting' in l['message'] for l in nas_logs)
        
        # Check tcpdump logs
        tcp_logs = [l for l in logs if l['service'] == 'tcpdump']
        assert len(tcp_logs) == 1
        assert tcp_logs[0]['message'] == "IP 10.8.0.2.27900 > 10.8.0.1.27900: UDP, length 18"
        assert tcp_logs[0]['level'] == 'info'

def test_get_system_stats():
    # Should not throw and should return valid types
    stats = get_system_stats(active_players=5)
    assert 'active_players' in stats
    assert 'pps' in stats
    assert 'db_latency' in stats
    assert 'cpu_load' in stats
    assert isinstance(stats['cpu_load'], float)
