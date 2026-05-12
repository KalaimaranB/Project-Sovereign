"""DWC Network Server Emulator

    Copyright (C) 2014 polaris-
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

Master server list server

Basic idea:
    The server listing does not need to be persistent, and it must be easily
    searchable for any unknown parameters. So instead of using a SQL database,
    I've opted to create a server list database server which communicates
    between the server browser and the qr server. The server list database
    will be stored in dictionaries as to allow dynamic columns that can be
    easily searched. The main reason for this configuration is because it
    cannot be guaranteed what data a game's server will required. For example,
    in addition to the common fields such as publicip, numplayers, dwc_pid,
    etc, Lost Magic also uses fields such as LMname, LMsecN, LMrating,
    LMbtmode, and LMversion.

    It would be possible to create game-specific databases but this would be
    more of a hassle and less universal. It would also be possible pickle a
    dictionary containing all of the fields and store it in a SQL database
    instead, but that would require unpickling every server each time you want
    to match search queries which would cause overhead if there are a lot of
    running servers. One trade off here is that we'll be using more memory by
    storing each server as a dictionary in the memory instead of storing it in
    a SQL database.

 - qr_server and server_browser both will act as clients to
   gs_server_database.
 - qr_server will send an add and/or delete to add or remove servers from the
   server list.
 - server_browser will send a request with the game name followed by optional
   search parameters to get a list of servers.
"""

import logging
import time
import ast

from other.sql import sql_commands, LIKE
import other.utils as utils
import dwc_config

from gamespy.redis_cache import RedisGamespyCacheSync

logger = dwc_config.get_logger('GameSpyManager')


class TokenType:
    UNKNOWN = 0
    FIELD = 1
    STRING = 2
    NUMBER = 3
    TOKEN = 4


class GameSpyBackendServer(object):
    def __init__(self):
        """
        Central interface realization for GameSpy query/reporting services.
        No longer enforces heavy IPC process locks. Talks directly to distributed cache.
        """
        self.cache = RedisGamespyCacheSync()

    def start(self):
        """NO-OP preserved for process harness backward compatibility. 
        Actual realization is now a stateless helper logic bank."""
        logger.log(logging.INFO, "Started local Redis-powered Backend library module.")

    def get_token(self, filters):
        """Complex example from Dungeon Explorer: Warriors of Ancient Arts
        dwc_mver = 3 and dwc_pid != 474890913 and maxplayers = 2 and
        numplayers < 2 and dwc_mtype = 0 and dwc_mresv != dwc_pid and
        (MatchType='english')

        Even more complex example from Phantasy Star Zero:
        dwc_mver = 3 and dwc_pid != 4 and maxplayers = 3 and
        numplayers < 3 and dwc_mtype = 0 and dwc_mresv != dwc_pid and
        (((20=auth)AND((1&mskdif)=mskdif)AND((14&mskstg)=mskstg)))

        Example with OR from Mario Kart Wii:
        dwc_mver = 90 and dwc_pid != 1 and maxplayers = 11 and
        numplayers < 11 and dwc_mtype = 0 and dwc_hoststate = 2 and
        dwc_suspend = 0 and (rk = 'vs_123' and (ev > 4263 or ev <= 5763)
        and p = 0)

        Example with LIKE from Fortune Street:
        dwc_mver = 90 and dwc_pid != 15 and maxplayers = 3 and
        numplayers < 3 and dwc_mtype = 0 and dwc_suspend = 0 and
        dwc_hoststate = 2 and ((zvar LIKE '102') AND (zmtp LIKE 'EU') AND
        (zrule LIKE '1') AND (zpnum LIKE '2') AND (zaddc LIKE '0') AND rel='1')
        """
        i = 0
        start = i
        special_chars = "_"

        token_type = TokenType.UNKNOWN

        # Skip whitespace
        while i < len(filters) and filters[i].isspace():
            i += 1
            start += 1

        if i < len(filters):
            if filters[i] == "(":
                i += 1
                token_type = TokenType.TOKEN

            elif filters[i] == ")":
                i += 1
                token_type = TokenType.TOKEN

            elif filters[i] == "&":
                i += 1
                token_type = TokenType.TOKEN

            elif filters[i] == "=":
                i += 1
                token_type = TokenType.TOKEN

            elif filters[i] == ">" or filters[i] == "<":
                i += 1
                token_type = TokenType.TOKEN

                if i < len(filters) and filters[i] == "=":
                    # >= or <=
                    i += 1

            elif i + 1 < len(filters) and filters[i] == "!" and \
                    filters[i + 1] == "=":
                i += 2
                token_type = TokenType.TOKEN

            elif filters[i] == "'":
                # String literal
                token_type = TokenType.STRING

                i += 1  # Skip quotation mark
                while i < len(filters) and filters[i] != "'":
                    i += 1

                if i < len(filters) and filters[i] == "'":
                    i += 1  # Skip quotation mark

            elif filters[i] == "\"":
                # I don't know if it's in the spec or not, but I added ""
                # string literals as well just in case.
                token_type = TokenType.STRING

                i += 1  # Skip quotation mark
                while i < len(filters) and filters[i] != "\"":
                    i += 1

                if i < len(filters) and filters[i] == "\"":
                    i += 1  # Skip quotation mark

            elif i + 1 < len(filters) and filters[i] == '-' and \
                    filters[i + 1].isdigit():
                # Negative number
                token_type = TokenType.NUMBER
                i += 1
                while i < len(filters) and filters[i].isdigit():
                    i += 1

            elif filters[i].isalnum() or filters[i] in special_chars:
                # Whole numbers or words
                if filters[i].isdigit():
                    token_type = TokenType.NUMBER
                elif filters[i].isalpha():
                    token_type = TokenType.FIELD

                while i < len(filters) and (filters[i].isalnum() or
                                            filters[i] in special_chars) and \
                        filters[i] not in "!=>< ":
                    i += 1

        token = filters[start:i]
        if token_type == TokenType.FIELD and \
           (token.lower() == "and" or token.lower() == "or"):
            token = token.lower()

        return token, i, token_type

    def translate_expression(self, filters):
        output = []
        variables = []

        while len(filters) > 0:
            token, i, token_type = self.get_token(filters)
            filters = filters[i:]

            if token_type == TokenType.TOKEN:
                # Python uses == instead of = for comparisons, so replace
                # it with the proper token for compilation.
                if token == "=":
                    token = "=="

            elif token_type == TokenType.FIELD:
                if token.upper() in sql_commands:
                    # Convert "A SQL_COMMAND B" into "A  |SQL_COMMAND| B"
                    output.extend(["|", token.upper(), "|"])
                    continue
                else:
                    # Each server has its own variables so handle it later.
                    variables.append(len(output))

            output.append(token)

        return output, variables

    def validate_ast(self, node, num_literal_only, is_sql=False):
        # This function tries to verify that the expression is a valid
        # expression before it gets evaluated.
        # Anything besides the whitelisted things below are strictly
        # forbidden:
        # - String literals
        # - Number literals
        # - Binary operators (CAN ONLY BE PERFORMED ON TWO NUMBER LITERALS)
        # - Comparisons (cannot use 'in', 'not in', 'is', 'is not' operators)
        #
        # Anything such as variables or arrays or function calls are NOT
        # VALID.
        # Never run the expression received from the client before running
        # this function on the expression first.
        # print type(node)

        # Only allow literals, comparisons, and math operations
        valid_node = False
        if isinstance(node, ast.Num):
            valid_node = True

        elif isinstance(node, ast.Str):
            if is_sql or not num_literal_only:
                valid_node = True

        elif isinstance(node, ast.BoolOp):
            for value in node.values:
                valid_node = self.validate_ast(value, num_literal_only)

                if not valid_node:
                    break

        elif isinstance(node, ast.BinOp):
            # Allow SQL_COMMAND infix operator with more types
            is_sql |= \
                hasattr(node, "left") and \
                hasattr(node.left, "right") and \
                isinstance(node.left.right, ast.Name) and \
                node.left.right.id in sql_commands
            valid_node = self.validate_ast(node.left, True, is_sql)

            if valid_node:
                valid_node = self.validate_ast(node.right, True, is_sql)

        elif isinstance(node, ast.UnaryOp):
            valid_node = self.validate_ast(node.operand, num_literal_only)

        elif isinstance(node, ast.Expr):
            valid_node = self.validate_ast(node.value, num_literal_only)

        elif isinstance(node, ast.Compare):
            valid_node = self.validate_ast(node.left, num_literal_only)

            for op in node.ops:
                # print type(op)

                # Restrict "is", "is not", "in", and "not in" python
                # comparison operators. These are python-specific and the
                # games have no way of knowing what they are, so there's no
                # reason to keep them around.
                if isinstance(op, ast.Is) or isinstance(op, ast.IsNot) or \
                   isinstance(op, ast.In) or isinstance(op, ast.NotIn):
                    valid_node = False
                    break

            if valid_node:
                for expr in node.comparators:
                    valid_node = self.validate_ast(expr, num_literal_only)

        elif isinstance(node, ast.Call):
            valid_node = False

        elif isinstance(node, ast.Name):
            valid_node = node.id in sql_commands

        return valid_node

    def find_servers(self, gameid, filters, fields, max_count):
        matched_servers = []
        
        active_list = self.cache.get_all_servers_for_game(gameid)
        if not active_list:
            return []

        start = time.time()

        for server in active_list:
            stop_search = False

            if filters:
                translated, variables = self.translate_expression(filters)

                for idx in variables:
                    token = translated[idx]

                    if token in server:
                        token = server[token]
                        _, _, token_type = self.get_token(token)

                        if token_type == TokenType.FIELD:
                            # At this point, any field should be a string.
                            # This does not support stuff like:
                            # dwc_test = 'test', dwc_test2 = dwc_test,
                            # dwc_test3 = dwc_test2
                            token = '"' + token + '"'

                        elif token_type == TokenType.NUMBER:
                            for idx2 in range(idx + 1, len(translated)):
                                _, _, token_type = \
                                    self.get_token(translated[idx2])

                                if token_type == TokenType.TOKEN and \
                                   translated[idx2] not in ('(', ')'):
                                    if idx2 == idx + 1:
                                        # Skip boolean operator if it's the
                                        # first token on the right
                                        continue

                                    # Boolean operator, leave left as integer
                                    token = str(int(token))
                                    break

                                elif token_type == TokenType.STRING or \
                                        token_type == TokenType.NUMBER:
                                    if token_type == TokenType.STRING:
                                        # Found string on far right, turn left
                                        # into string as well
                                        token = "'" + token + "'"
                                    elif token_type == TokenType.NUMBER:
                                        token = str(int(token))
                                    break

                        translated[idx] = token

                q = ' '.join(translated)

                # Always run validate_ast over the entire AST before
                # evaluating anything. eval() is dangerous to use on
                # unsanitized inputs. The validate_ast function has a fairly
                # strict whitelist so it should be safe in what it accepts as
                # valid.
                m = ast.parse(q, "<string>", "exec")
                valid_filter = True
                for node in m.body:
                    valid_filter = self.validate_ast(node, False)

                if not valid_filter:
                    # Return only anything matched up until this point.
                    logger.log(logging.WARNING,
                               "Invalid filter(s): %s",
                               filters)
                    # stop_search = True
                    continue
                else:
                    # Use Python to evaluate the query. This method may take a
                    # little time but it shouldn't be all that big of a
                    # difference, I think. It takes about 0.0004 seconds per
                    # server to determine whether or not it's a match on my
                    # computer. Usually there's a low max_servers set when the
                    # game searches for servers, so assuming something like
                    # the game is asking for 6 servers, it would take about
                    # 0.0024 seconds total. These times will obviously be
                    # different per computer. It's not ideal, but it shouldn't
                    # be a huge bottleneck. A possible way to speed it up is
                    # to make validate_ast also evaluate the expressions at
                    # the same time as it validates it.
                    result = eval(q)
            else:
                # There are no filters, so just return the server.
                result = True
                valid_filter = True

            if stop_search:
                break

            if valid_filter and result:
                matched_servers.append(server)

                if max_count and len(matched_servers) >= max_count:
                    break

        servers = []
        for server in matched_servers:
            # Create a result with only the fields requested
            result = {}

            # Return all localips
            i = 0
            while 'localip' + str(i) in server:
                result['localip' + str(i)] = server['localip' + str(i)]
                i += 1

            attrs = [
                    "localport", "natneg",
                    "publicip", "publicport",
                    "__session__", "__console__"
            ]
            result.update({name: server[name]
                           for name in attrs if name in server})

            requested = {}
            for field in fields:
                # if not field in result:
                if field in server:
                    requested[field] = server[field]
                else:
                    # Return a dummy value. What's the normal behavior of
                    # the real server in this case?
                    requested[field] = ""

            result['requested'] = requested
            servers.append(result)

        logger.log(logging.DEBUG,
                   "Matched %d servers in %s seconds",
                   len(servers), (time.time() - start))

        return servers

    def update_server_list(self, gameid, session, value, console):
        """Refreshes dynamic server presence in backend Redis matrix with atomic eviction safety."""
        self.delete_server(gameid, session)

        value['__session__'] = session
        value['__console__'] = console

        logger.log(logging.DEBUG, "Added %s to the server list for %s", value, gameid)
        # Apply absolute 60 second TTL explicitly on upsert to prevent ghost artifacts
        self.cache.upsert_server(gameid, session, value, ttl_seconds=60)

        return value

    def delete_server(self, gameid, session):
        self.cache.delete_server(gameid, session)
        logger.log(logging.DEBUG, "Deleted %s server where session = %d", gameid, session)

    def find_server_by_address(self, ip, port, gameid=None):
        active_list = self.cache.get_all_servers_for_game(gameid)
        for server in active_list:
            if server['publicip'] == ip and (not port or server['publicport'] == str(port)):
                 return server
        return None

    def find_server_by_local_address(self, publicip, localaddr, gameid=None):
        localip = localaddr[0]
        localport = localaddr[1]

        active_list = self.cache.get_all_servers_for_game(gameid)
        best_match = None

        for server in active_list:
             if server['publicip'] == publicip:
                 if server.get('localport') == str(localport):
                     return server
                 for x in range(0, 10):
                     if server.get(f'localip{x}') == localip:
                         best_match = server
                 if not localport and best_match is None:
                     best_match = server
        return best_match

    def add_natneg_server(self, cookie, server):
        logger.log(logging.DEBUG, "Added natneg server %d", cookie)
        self.cache.add_natneg_server(cookie, server)

    def get_natneg_server(self, cookie):
        res = self.cache.get_natneg_servers(cookie)
        return res if res else None

    def delete_natneg_server(self, cookie):
        self.cache.delete_natneg_server(cookie)
        logger.log(logging.DEBUG, "Deleted natneg server %d", cookie)

if __name__ == '__main__':
    backend_server = GameSpyBackendServer()
    backend_server.start()
    # Hold daemon active temporarily to simulate old behaviour
    while True: time.sleep(10)
