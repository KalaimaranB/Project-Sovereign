"""DWC Network Server Emulator - Modernized Profile Server

    Refactored utilizing Python 3 asyncio streams. 
    Completely severed twisted.internet dependency stack.
"""

import asyncio
import logging
import sys
import os
from other import metrics

import dwc_config
from gamespy import gs_database
from gamespy.pg_database import PostgresGamespyDatabase
from gamespy.profile_protocol import ProfileProtocol, ResponseEffect, RouteEffect, StateUpdateEffect

logger = dwc_config.get_logger('GameSpyProfileServer')

class SessionGlobalContext:
    """
    Serves as the communication bridge context required by logic protocols
    to transparently peer query without holding circular transport pointers.
    """
    def __init__(self):
        self.pid_map = {} # ProfileID -> AsyncSessionHandler
        
    def register(self, profileid, handler):
        self.pid_map[profileid] = handler
        
    def unregister(self, profileid):
        if profileid in self.pid_map:
            del self.pid_map[profileid]

    def get_active_profile(self, profileid):
        """Fulfills logic context requirement querying specific connection info."""
        handler = self.pid_map.get(profileid)
        if not handler:
            return None
            
        # Read properties from logic safely
        return {
            'gameid': handler.logic.gameid,
            'status': handler.logic.status,
            'statstring': handler.logic.statstring,
            'locstring': handler.logic.locstring,
        }
        
    def get_handler(self, profileid):
        return self.pid_map.get(profileid)

class AsyncSessionHandler:
    """
    Responsible purely for mapping asyncio.Stream elements into Protocol triggers,
    and propagating Protocol side effects back into streams.
    """
    def __init__(self, reader, writer, global_ctx, db):
        self.reader = reader
        self.writer = writer
        self.ctx = global_ctx
        
        addr = writer.get_extra_info('peername')
        self.peer = addr
        
        # Setup actual state machine logic with dependency injection
        self.logic = ProfileProtocol(
            db=db, 
            address=addr, 
            context_provider=self.ctx
        )
        
    def write(self, data):
        try:
            self.writer.write(data)
        except Exception:
             pass # Stream potentially closed, cleaner handled by run loop breaking
             
    async def flush(self):
        try:
            await self.writer.drain()
        except Exception:
            pass

    def process_effects(self, effects):
        """Dispatcher looping through logic emitted events."""
        for effect in effects:
            if isinstance(effect, ResponseEffect):
                 self.write(effect.data)
            
            elif isinstance(effect, RouteEffect):
                 target = self.ctx.get_handler(effect.target_profileid)
                 if target:
                      target.write(effect.data)
                      # Note: No explicit drain here to prevent buffering lockups on fast broadcast bursts
                      
            elif isinstance(effect, StateUpdateEffect):
                 if effect.event == 'register_global_session':
                      self.ctx.register(effect.payload, self)
                 elif effect.event == 'delete_global_session':
                      self.ctx.unregister(effect.payload)

    async def run(self):
        logger.info("New stream opened from %s", self.peer)
        metrics.increment_connections('profile')

        
        # Trigger initial greeting handshake logic
        initial = self.logic.on_connection_made()
        self.process_effects(initial)
        await self.flush()
        
        try:
            while True:
                chunk = await self.reader.read(1024)
                if not chunk:
                    break # End of stream marker
                    
                # Perform logic evaluation
                action_effects = self.logic.on_data_received(chunk)
                
                # Side-effect dispatch
                self.process_effects(action_effects)
                await self.flush()
                
        except (asyncio.IncompleteReadError, ConnectionResetError, BrokenPipeError):
             logger.warning("TCP disconnection during active stream from %s", self.peer)
        except Exception as e:
             logger.error("Terminal handler exception: %s", e)
        finally:
             metrics.decrement_connections('profile')
             # Trigger teardown protocol and ensure disconnected properly
             logger.info("Releasing stream handles for %s", self.peer)
             exit_effects = await self.logic.on_connection_lost()
             self.process_effects(exit_effects)
             
             try:
                 self.writer.close()
                 await self.writer.wait_closed()
             except Exception:
                 pass

class GameSpyProfileServer:
    """Modern replacement providing legacy startup lifecycle contract."""
    def __init__(self):
        self.ctx = SessionGlobalContext()
        # Dynamically utilizing our modernized high-performance PostgreSQL engine
        self.db = PostgresGamespyDatabase()
        
    async def client_connected_cb(self, reader, writer):
        handler = AsyncSessionHandler(reader, writer, self.ctx, self.db)
        await handler.run()

    async def main(self):
        # 0. Launch centralized telemetry scraper endpoint
        metrics_port = int(os.environ.get('METRICS_PORT', 9100))
        metrics.launch_metrics_endpoint(metrics_port)

        # 1. Establish the shared async connection pool once globally
        await self.db.initialize_database()
        
        ip, port = dwc_config.get_ip_port('GameSpyProfileServer')
        logger.info("Establishing Async Profile TCP server on %s:%d", ip, port)
        
        server = await asyncio.start_server(self.client_connected_cb, ip, port)
        addr = server.sockets[0].getsockname()
        logger.info(f'Serving actively on {addr}')

        async with server:
            await server.serve_forever()

    def start(self):
        asyncio.run(self.main())

if __name__ == "__main__":
    srv = GameSpyProfileServer()
    srv.start()
