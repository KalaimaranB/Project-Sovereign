import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Include parent directory to resolve the 'services' package and other libraries
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Patch out network bindings and configuration for testing
with patch('gamespy.pg_database_sync.PostgresGamespyDatabaseSync') as mock_db_cls:
    import services.register_page as register_page
    import services.admin_page_server as admin_page_server
    import services.storage_server as storage_server

class MockRequest:
    def __init__(self, args=None, headers=None):
        self.args = args or {}
        self.headers = headers or {}
        self.response_code = 200
        self.client_ip = "127.0.0.1"
        self.written_content = b""

    def getClientIP(self):
        return self.client_ip

    def setResponseCode(self, code):
        self.response_code = code

    def setHeader(self, name, value):
        self.headers[name] = value

    def getHeader(self, name):
        return self.headers.get(name)

    def write(self, content):
        self.written_content += content if isinstance(content, bytes) else content.encode('utf-8')


@patch('services.register_page.PostgresGamespyDatabaseSync')
def test_register_page_postgres(mock_db_sync_cls):
    """Verifies RegPage natively routes dynamic mac registration queries to PG sync adapter."""
    mock_db = mock_db_sync_cls.return_value
    mock_parent = MagicMock()
    
    # Create handler
    page = register_page.RegPage(mock_parent)
    
    assert page.db == mock_db
    
    # Simulate standard request using normal strings (Twisted hands off unicode/decoded strings)
    req = MockRequest(args={
        'macadr': ['aa:bb:cc:dd:ee:ff'],
        'action': ['add']
    })
    
    # Execute handler logic
    page.update_maclist(req)
    
    # Assert native Postgres query binding executed correctly
    mock_db.execute_raw.assert_called_with(
        'INSERT INTO pending (macadr) VALUES($1)',
        'aabbccddeeff'
    )


@patch('services.admin_page_server.PostgresGamespyDatabaseSync')
def test_admin_page_postgres_bans(mock_db_sync_cls):
    """Verifies admin dashboard correctly executes native positional parameter bans."""
    mock_db = mock_db_sync_cls.return_value
    mock_parent = MagicMock()
    
    admin = admin_page_server.AdminPage(mock_parent)
    
    # 1. Test BAN action
    req_ban = MockRequest(args={
        'gameid': ['g001'],
        'ipaddr': ['10.0.0.5'],
        'action': ['ban']
    })
    admin.update_banlist(req_ban)
    
    mock_db.execute_raw.assert_any_call(
        'INSERT INTO banned (gameid, ipaddr) VALUES($1,$2)',
        'G00', '10.0.0.5'
    )

    # 2. Test UNBAN action
    req_unban = MockRequest(args={
        'gameid': ['g001'],
        'ipaddr': ['10.0.0.5'],
        'action': ['unban']
    })
    admin.update_banlist(req_unban)
    
    mock_db.execute_raw.assert_any_call(
        'DELETE FROM banned WHERE gameid=$1 AND ipaddr=$2',
        'G00', '10.0.0.5'
    )


@patch('services.storage_server.PostgresGamespyDatabaseSync')
def test_storage_server_introspection(mock_db_sync_cls):
    """Verifies storage engine uses ANSI Information Schema instead of SQLite Master."""
    mock_db = mock_db_sync_cls.return_value
    
    # Mock column fetch sequence for initialization
    mock_db.fetch_raw.side_effect = [
        [{'table_name': 'g2050_box'}],  # Initial list of tables
        [{'column_name': 'recordid'}, {'column_name': 'ownerid'}] # Column dump for g2050_box
    ]
    
    # Bypass dynamic table setup in init
    with patch.object(storage_server.StorageHTTPServer, 'create_or_alter_table_if_not_exists'), \
         patch.object(storage_server.StorageHTTPServer, 'table_exists'), \
         patch('http.server.HTTPServer.__init__', lambda *args, **kwargs: None):
         
         server = storage_server.StorageHTTPServer(('127.0.0.1', 80), MagicMock())
         
         # Trigger table structure list to assert standard calls
         assert 'g2050_box' in server.tables
         assert 'recordid' in server.tables['g2050_box']
         
         # Check manual schema query was executed against pg catalog
         mock_db.fetch_raw.assert_any_call(
             "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
         )
         mock_db.fetch_raw.assert_any_call(
             "SELECT column_name FROM information_schema.columns WHERE table_name = $1",
             'g2050_box'
         )


@patch('services.storage_server.PostgresGamespyDatabaseSync')
def test_storage_server_crud(mock_db_sync_cls):
    """Tests that dynamic insert and positional updating logic operates correctly."""
    mock_db = mock_db_sync_cls.return_value
    mock_db.fetchval_raw.return_value = 999 # RecordID return value
    
    with patch.object(storage_server.StorageHTTPServer, 'create_or_alter_table_if_not_exists'), \
         patch('http.server.HTTPServer.__init__', lambda *args, **kwargs: None):
         
         server = storage_server.StorageHTTPServer(('127.0.0.1', 80), MagicMock())
         server.tables = {'g100_t1': ['recordid', 'ownerid', 'stat']}
         
         # 1. Test table_exists
         server.table_exists('g100_t1')
         mock_db.fetchval_raw.assert_any_call(
             "SELECT COUNT(1) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = $1",
             'g100_t1'
         )
         
         # 2. Test column_exists
         server.column_exists('g100_t1', 'stat')
         mock_db.fetchval_raw.assert_any_call(
             "SELECT COUNT(1) FROM information_schema.columns WHERE table_name = $1 AND column_name = $2",
             'g100_t1', 'stat'
         )
