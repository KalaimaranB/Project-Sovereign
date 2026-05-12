"""DWC Network Server Emulator

    Copyright (C) 2014 polaris-
    Copyright (C) 2014 msoucy
    Copyright (C) 2015 Sepalani

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from twisted.web import server, resource
from twisted.internet import reactor
from twisted.internet.error import ReactorAlreadyRunning
import time
import datetime
import json
import logging

from gamespy.redis_cache import RedisGamespyCacheSync

import other.utils as utils
import dwc_config

logger = dwc_config.get_logger('InternalStatsServer')


# Legacy multi-process class removed in favor of pure stateless Redis aggregation.


class StatsPage(resource.Resource):
    """Servers statistics webpage.

    Format attributes:
     - header
     - row
     - footer
    """
    isLeaf = True
    header = """<html>
    <table border='1'>
        <tr>
            <td>Game ID</td><td># Players</td>
        </tr>"""
    row = """
        <tr>
            <td>%s</td>
            <td><center>%d</center></td>
        </tr>"""  # % (game, len(server_list[game]))
    footer = """</table>
    <br>
    <i>Last updated: %s</i><br>
    </html>"""  # % (self.stats.get_last_update_time())

    def __init__(self, stats):
        self.stats = stats

    def render_GET(self, request):
        if "/".join(request.postpath) == "json":
            raw = True
            force_update = True
        else:
            raw = False
            force_update = False

        server_list = self.stats.get_server_list(force_update)

        if raw:
            # List of keys to be removed
            restricted = ["publicip", "__session__", "localip0", "localip1"]

            # Filter out certain fields before displaying raw data
            if server_list is not None:
                for game in server_list:
                    for server in server_list[game]:
                        for r in restricted:
                            if r in server:
                                server.pop(r, None)

            output = json.dumps(server_list)

        else:
            output = self.header
            if server_list is not None:
                output += "".join(self.row % (game, len(server_list[game]))
                                  for game in server_list
                                  if server_list[game])
            output += self.footer % (self.stats.get_last_update_time())

        return output


class InternalStatsServer(object):
    """Internal Statistics server.

    Running on port 9001 by default: http://127.0.0.1:9001/
    Can be displayed in json format: http://127.0.0.1:9001/json
    """
    def __init__(self):
        self.last_update = 0
        self.next_update = 0
        self.server_list = None
        # The number of seconds to wait before updating the server list
        self.seconds_per_update = 60

    def start(self):
        # Connect to modern stateless Redis aggregation instead of coupled legacy manager
        self.cache = RedisGamespyCacheSync()

        site = server.Site(StatsPage(self))
        reactor.listenTCP(dwc_config.get_port('InternalStatsServer'), site)

        try:
            if not reactor.running:
                reactor.run(installSignalHandlers=0)
        except ReactorAlreadyRunning:
            pass

    def get_server_list(self, force_update=False):
        if force_update or self.next_update == 0 or \
           self.next_update - time.time() <= 0:
            self.last_update = time.time()
            self.next_update = time.time() + self.seconds_per_update
            
            # Direct stateless pull of the entire system fleet simultaneously
            raw_list = self.cache.get_all_servers_for_game()
            
            # Transform flattened list back into the legacy nested grouped dict {gamename: [servers]}
            # to satisfy the existing html/json rendering logic perfectly.
            grouped = {}
            for s in raw_list:
                gname = s.get('gamename', 'unknown')
                if gname not in grouped:
                    grouped[gname] = []
                grouped[gname].append(s)
                
            self.server_list = grouped
            logger.log(logging.DEBUG, "Fetched %d servers across %d titles.", len(raw_list), len(grouped))

        return self.server_list

    def get_last_update_time(self):
        return str(datetime.datetime.fromtimestamp(self.last_update))


if __name__ == "__main__":
    stats = InternalStatsServer()
    stats.start()
