import threading
import asyncio
import inspect
import os
import sys

# Safeguard dynamic execution pathways regardless of caller context
try:
    from gamespy.pg_database import PostgresGamespyDatabase
except ImportError:
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))
    from pg_database import PostgresGamespyDatabase

class PostgresGamespyDatabaseSync:
    """
    Universal Synchronous Proxy Adapter leveraging automated dynamic meta-forwarding.
    Safely delivers native AsyncPG capability to legacy synchronous thread clusters.
    """
    def __init__(self, dsn=None):
        # Setup localized singleton event loop bound exclusively to this instance
        self._loop = asyncio.new_event_loop()
        self.async_db = PostgresGamespyDatabase(dsn)
        
        def _worker():
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()
            
        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()
        
        # Force blocking initialization anchoring connection pool existence
        self._call(self.async_db.initialize_database())

    def _call(self, coro):
        """
        Direct gateway submission logic executing generalized coroutines 
        (including complex utilities) securely within total event-loop isolation.
        """
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def __getattr__(self, name):
        """
        The ultimate SOLID proxy router. Automatically identifies any backend method 
        declared as 'async def' and transparently dispatches it to blocking execution.
        """
        attr = getattr(self.async_db, name)
        
        if inspect.iscoroutinefunction(attr):
            def proxy_wrapper(*args, **kwargs):
                return self._call(attr(*args, **kwargs))
            return proxy_wrapper
            
        return attr
    
    def close(self):
        """Atomic termination handler securing connection release protocols."""
        if hasattr(self, 'async_db'):
            try:
                self._call(self.async_db.close())
            except Exception:
                pass
        if hasattr(self, '_loop'):
            self._loop.call_soon_threadsafe(self._loop.stop)
