import pytest
import os
import sys
from prometheus_client import REGISTRY

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from other import metrics

def test_metrics_connections_increment():
    """Verifies connection gauges update correctly."""
    initial_value = REGISTRY.get_sample_value('gamespy_active_connections', {'service': 'profile_test'}) or 0.0
    
    metrics.increment_connections('profile_test')
    new_value = REGISTRY.get_sample_value('gamespy_active_connections', {'service': 'profile_test'})
    
    assert new_value == initial_value + 1.0, "Connection gauge must increment by 1."
    
    metrics.decrement_connections('profile_test')
    decremented_value = REGISTRY.get_sample_value('gamespy_active_connections', {'service': 'profile_test'})
    
    assert decremented_value == initial_value, "Connection gauge must return to baseline after decrement."

def test_metrics_packet_recording():
    """Verifies packet counters accumulate properly across distinct commands."""
    base_count = REGISTRY.get_sample_value('gamespy_packets_total', {'service': 'natneg_test', 'cmd': 'NN_INIT'}) or 0.0
    
    metrics.record_packet('natneg_test', 'NN_INIT')
    metrics.record_packet('natneg_test', 'NN_INIT')
    
    current_count = REGISTRY.get_sample_value('gamespy_packets_total', {'service': 'natneg_test', 'cmd': 'NN_INIT'})
    
    assert current_count == base_count + 2.0, "Packet counts must increment consistently."

def test_metrics_http_records():
    """Verifies HTTP tracking registers distinct endpoints."""
    base = REGISTRY.get_sample_value('http_requests_total', {'service': 'nas_test', 'endpoint': '/ac', 'status': '200'}) or 0.0
    
    metrics.record_http_request('nas_test', '/ac', 200)
    
    current = REGISTRY.get_sample_value('http_requests_total', {'service': 'nas_test', 'endpoint': '/ac', 'status': '200'})
    
    assert current == base + 1.0, "HTTP requests counter must record success states accurately."
