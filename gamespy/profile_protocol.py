import time
import logging
import traceback
from collections import namedtuple

import other.utils as utils
import gamespy.gs_query as gs_query
import gamespy.gs_utility as gs_utility
from other import metrics


logger = logging.getLogger('GameSpyProfileServer')

# Output payloads for non-blocking IO integration layer
ResponseEffect = namedtuple('ResponseEffect', ['data'])
RouteEffect = namedtuple('RouteEffect', ['target_profileid', 'data'])
StateUpdateEffect = namedtuple('StateUpdateEffect', ['event', 'payload'])

class ProfileProtocol:
    """
    Pure business logic decoupled state machine for GameSpy Profile TCP handling.
    Replaces original Twisted PlayerSession implementation.
    """
    def __init__(self, db, address, context_provider=None):
        """
        :param db: Validated GS database reference (SOLID Injected)
        :param address: Tuple containing hostname/port
        :param context_provider: Callback allowing logic layer to query active global sessions info safely
        """
        self.db = db
        self.host = address[0]
        self.port = address[1]
        self.context_provider = context_provider
        
        self.remaining_message = ""
        self.profileid = 0
        self.gameid = ""
        
        self.buddies = []
        self.blocked = []
        
        self.status = "0"
        self.statstring = ""
        self.locstring = ""
        
        self.keepalive = int(time.time())
        self.sesskey = ""
        self.sdkrevision = "0"
        
        self.challenge = ""

    def _log(self, level, msg, *args):
        prefix = f"[{self.host}:{self.port}"
        if self.profileid:
            prefix += f" | {self.profileid}"
        if self.gameid:
            prefix += f" | {self.gameid}"
        prefix += "] "
        logger.log(level, prefix + msg, *args)

    def on_connection_made(self):
        """Hook to yield initial payload when socket initially establishes."""
        self._log(logging.INFO, "Initialized protocol session")
        
        # Seed verification challenge
        self.challenge = utils.generate_random_str(10, "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        
        msg = gs_query.create_gamespy_message([
            ('__cmd__', "lc"),
            ('__cmd_val__', "1"),
            ('challenge', self.challenge),
            ('id', "1"),
        ])
        
        return [ResponseEffect(data=msg.encode('latin-1'))]

    async def on_connection_lost(self):
        """Cleans up external persistent states, returning closing side effects."""
        self._log(logging.INFO, "Protocol marked for disconnection")
        
        effects = []
        
        # Move to offline and update friends
        self.status = "0"
        self.statstring = "Offline"
        self.locstring = ""
        
        effects.extend(await self._yield_status_to_friends())
        
        # Dispatch final deletion triggers to wrapper
        if self.profileid:
             effects.append(StateUpdateEffect('delete_global_session', self.profileid))
             
        # Cleanly delete any existing persistent session
        if self.sesskey:
             await self.db.delete_session(self.profileid)
             
        return effects

    async def on_data_received(self, chunk):
        """Processes incremental network data buffer, handles slicing, returns generated effects."""
        effects = []
        
        try:
            # Auto normalize to string using latin-1 to mirror original Python 2 flow precisely
            current_str = chunk.decode('latin-1') if isinstance(chunk, bytes) else chunk
            logger.debug("RESPONSE: '%s'...", current_str[:200])  # Log raw received data (truncated)
            
            full_data = self.remaining_message + current_str
            
            # Replicate buffer stabilization logic precisely
            if len(full_data) > 0 and not full_data.startswith('\\'):
                 final_mark = "\\final\\"
                 if final_mark in full_data:
                     full_data = full_data[full_data.index(final_mark) + len(final_mark):]
                 else:
                     full_data = ""
                     
            commands, self.remaining_message = gs_query.parse_gamespy_message(full_data)
            
            dispatcher = {
                "login": self._perform_login,
                "logout": self._perform_logout,
                "getprofile": self._perform_getprofile,
                "updatepro": self._perform_updatepro,
                "ka": self._perform_ka,
                "status": self._perform_status,
                "bm": self._perform_bm,
                "addbuddy": self._perform_addbuddy,
                "delbuddy": self._perform_delbuddy,
                "authadd": self._perform_authadd,
            }
            
            for cmd in commands:
                self._log(logging.DEBUG, "Processing COMMAND: %s", cmd)
                cmd_name = cmd.get('__cmd__') or 'unknown'
                metrics.record_packet('profile', cmd_name)
                handler = dispatcher.get(cmd_name)
                if handler:
                    res = await handler(cmd)
                    if res:
                        effects.extend(res)
                        for eff in res:
                            if isinstance(eff, ResponseEffect):
                                self._log(logging.DEBUG, "SENDING: '%s'...",
                                          eff.data.decode('latin-1', errors='replace')[:200])
                else:
                    self._log(logging.ERROR, "Unknown protocol command rejected: '%s'", cmd.get('__cmd__'))
                    
        except Exception:
            self._log(logging.ERROR, "Critical parse exception: %s", traceback.format_exc())
            
        return effects

    # --- Internal Dispatch Implementation Blocks ---
    
    async def _perform_login(self, data):
        eff = []
        
        authtoken_parsed = await gs_utility.parse_authtoken(data.get('authtoken', ''), self.db)
        
        if authtoken_parsed is None:
             self._log(logging.WARNING, "Auth token invalid for login attempt.")
             msg = gs_query.create_gamespy_message([
                ('__cmd__', "error"),
                ('__cmd_val__', ""),
                ('err', '266'),
                ('fatal', ''),
                ('errmsg', 'There was an error validating the pre-authentication.'),
                ('id', data.get('id', '1')),
             ])
             eff.append(ResponseEffect(msg.encode('latin-1')))
             return eff

        if 'sdkrevision' in data:
            self.sdkrevision = data['sdkrevision']
             
        userid, profileid, gsbrcd, uniquenick = await gs_utility.login_profile_via_parsed_authtoken(authtoken_parsed, self.db)
        self.gameid = gsbrcd[:4] if gsbrcd else ""
        
        # Challenge Response Hash Matching
        calculated_response = gs_utility.generate_response(
            self.challenge, authtoken_parsed.get('challenge', ''),
            data.get('challenge', ''), data.get('authtoken', '')
        )
        
        if calculated_response != data.get('response'):
            self._log(logging.WARNING, "Login signature failed match.")
            msg = gs_query.create_gamespy_message([
                ('__cmd__', "error"),
                ('err', '266'),
                ('fatal', ''),
                ('errmsg', 'Invalid response.'),
                ('id', data.get('id', '1')),
            ])
            eff.append(ResponseEffect(msg.encode('latin-1')))
            return eff

        # Handle failed login — matches reference error 256
        if profileid is None:
            self._log(logging.INFO, "Invalid password or banned user")
            msg = gs_query.create_gamespy_message([
                ('__cmd__', "error"),
                ('__cmd_val__', ""),
                ('err', '256'),
                ('fatal', ''),
                ('errmsg', 'Login failed.'),
                ('id', data.get('id', '1')),
            ])
            eff.append(ResponseEffect(msg.encode('latin-1')))
            return eff

        # Check for duplicate session interference
        if self.context_provider and self.context_provider.get_active_profile(profileid):
             self._log(logging.INFO, "Forcibly disconnecting concurrent session conflict for PID %d", profileid)
             eff.append(RouteEffect(profileid, gs_query.create_gamespy_message([
                 ('__cmd__', 'logout'), ('reason', 'Another user has logged in.'),
             ]).encode('latin-1')))
             # Also yield a command to wrap wrapper memory
             eff.append(StateUpdateEffect('delete_global_session', profileid))

        # Successful Login
        self.profileid = profileid
        self._log(logging.INFO, "Login success: profileid=%d uniquenick=%s", profileid, uniquenick)
        eff.append(StateUpdateEffect('register_global_session', profileid))
        
        # Pull relationships (Updated to use accurate legacy names)
        self.buddies = await self.db.get_buddy_list(profileid)
        self.blocked = await self.db.get_blocked_list(profileid)
        
        # Generate a proper random loginticket — reference never reuses authtoken
        loginticket = gs_utility.base64_encode(
            utils.generate_random_str(16).encode('latin-1')
        ).decode('latin-1')
        self.sesskey = await self.db.create_session(self.profileid, loginticket)
        
        proof = gs_utility.generate_proof(
             self.challenge, authtoken_parsed.get('challenge', ''),
             data.get('challenge', ''), data.get('authtoken', '')
        )

        # sdkrevision 11 (Tatsunoko vs Capcom): send blk/bdy before lc\2
        if self.sdkrevision == "11":
            def make_id_list(lst):
                return [str(d['buddyProfileId']) for d in lst if d.get('status') == 1]

            block_list = make_id_list(self.blocked)
            blk_msg = gs_query.create_gamespy_message([
                ('__cmd__', "blk"), ('__cmd_val__', str(len(block_list))),
                ('list', ','.join(block_list)),
            ])
            self._log(logging.DEBUG, "SENDING: %s", blk_msg)
            eff.append(ResponseEffect(blk_msg.encode('latin-1')))

            buddy_list = make_id_list(self.buddies)
            bdy_msg = gs_query.create_gamespy_message([
                ('__cmd__', "bdy"), ('__cmd_val__', str(len(buddy_list))),
                ('list', ','.join(buddy_list)),
            ])
            self._log(logging.DEBUG, "SENDING: %s", bdy_msg)
            eff.append(ResponseEffect(bdy_msg.encode('latin-1')))

        login_res = gs_query.create_gamespy_message([
            ('__cmd__', "lc"), ('__cmd_val__', "2"),
            ('sesskey', self.sesskey),
            ('proof', proof),
            ('userid', str(userid)),
            ('profileid', str(self.profileid)),
            ('uniquenick', uniquenick),
            ('lt', loginticket),
            ('id', data.get('id', '1')),
        ])
        self._log(logging.DEBUG, "SENDING: %s", login_res)
        eff.append(ResponseEffect(login_res.encode('latin-1')))
        
        # Pull buddies and notify online state
        self.status = "1"
        self.statstring = "Online"
        eff.extend(await self._yield_status_to_friends())
        
        # Fetch incoming offline buddy messages and automatically cycle deletion
        waiting_bms = await self.db.get_pending_messages(self.profileid)
        for bm in waiting_bms:
             # Wrapped in message wrapper check to accommodate actual list dict format later
             msg_val = bm['msg'] if isinstance(bm, dict) else bm
             eff.append(ResponseEffect(msg_val.encode('latin-1')))
             
        return eff

    async def _perform_logout(self, data):
        eff = []
        self._log(logging.INFO, "Client disconnected")
        self.status = "0"
        self.statstring = "Offline"
        eff.extend(await self._yield_status_to_friends())
        
        if self.profileid:
             eff.append(StateUpdateEffect('delete_global_session', self.profileid))
             self.profileid = 0
             
        return eff

    async def _perform_getprofile(self, data):
        profile = await self.db.get_profile_from_profileid(int(data.get('profileid', 0)))
        if not profile:
            return []
            
        # Map SQL key formats to exact output formatting exactly matching legacy
        resp_map = [
            ('__cmd__', "getprofile"), ('__cmd_val__', "1"),
            ('profileid', str(profile['profileid'])),
            ('nick', profile['nick'] if 'nick' in profile else profile['uniquenick']),
            ('userid', str(profile['userid'])),
            ('email', profile['email']), 
            ('sig', profile['sig'] if 'sig' in profile else ""),
            ('uniquenick', profile['uniquenick']),
            ('pid', str(profile['profileid'])),
            ('firstname', profile['firstname']),
            ('lastname', profile['lastname']),
            ('countrycode', profile['countrycode'] if 'countrycode' in profile else ""),
            ('id', data.get('id', '1'))
        ]
        return [ResponseEffect(gs_query.create_gamespy_message(resp_map).encode('latin-1'))]

    async def _perform_updatepro(self, data):
        # Field filtering cleanup
        sanitized = {k: v for k,v in data.items() if k not in ['__cmd__', '__cmd_val__', 'id', 'sesskey']}
        await self.db.update_profile(self.profileid, sanitized)
        
        resp = gs_query.create_gamespy_message([
             ('__cmd__', 'updatepro'), ('__cmd_val__', '1'),
             ('id', data.get('id', '1'))
        ])
        return [ResponseEffect(resp.encode('latin-1'))]

    async def _perform_ka(self, data):
        self.keepalive = int(time.time())
        # Return direct duplicate response just like legacy
        resp = gs_query.create_gamespy_message([('__cmd__', 'ka'), ('__cmd_val__', '')])
        return [ResponseEffect(resp.encode('latin-1'))]

    async def _perform_status(self, data):
        self.status = data.get('status', '0')
        self.statstring = data.get('statstring', '')
        self.locstring = data.get('locstring', '')
        
        # Propagate immediate status shift to entire buddy graph
        return await self._yield_status_to_friends()

    async def _perform_bm(self, data):
        # Buddy Message Distribution
        eff = []
        target_pid = int(data.get('t', 0))
        bm_type = data.get('__cmd_val__')
        
        out_msg = gs_query.create_gamespy_message([
             ('__cmd__', 'bm'), ('__cmd_val__', bm_type),
             ('f', str(self.profileid)),
             ('msg', data.get('msg', ''))
        ])
        
        # Legacy logic explicitly allowed type 100 responses back instantly
        if bm_type == "100":
             resp_confirm = gs_query.create_gamespy_message([
                  ('__cmd__', 'bm'), ('__cmd_val__', '100'),
                  ('f', str(target_pid)), ('msg', 'Success')
             ])
             eff.append(ResponseEffect(resp_confirm.encode('latin-1')))
             
        # If online, route immediately via dispatcher. Else store in SQL db queue.
        if self.context_provider and self.context_provider.get_active_profile(target_pid):
             eff.append(RouteEffect(target_pid, out_msg.encode('latin-1')))
        else:
             # Accurate alignment to "save_pending_message"
             await self.db.save_pending_message(self.profileid, target_pid, out_msg)
             
        return eff

    async def _perform_addbuddy(self, data):
        eff = []
        new_pid = int(data.get('newprofileid', 0))
        
        await self.db.add_buddy(self.profileid, new_pid)
        # Update local cache
        self.buddies = await self.db.get_buddy_list(self.profileid)
        
        # Cross notify request if online
        req_msg = gs_query.create_gamespy_message([
             ('__cmd__', 'br'), ('__cmd_val__', '1'),
             ('f', str(self.profileid)),
             ('msg', data.get('reason', 'Please add me!'))
        ])
        
        if self.context_provider and self.context_provider.get_active_profile(new_pid):
             eff.append(RouteEffect(new_pid, req_msg.encode('latin-1')))
             
        return eff

    async def _perform_delbuddy(self, data):
        target = int(data.get('delprofileid', 0))
        await self.db.delete_buddy(self.profileid, target)
        self.buddies = await self.db.get_buddy_list(self.profileid)
        return []

    async def _perform_authadd(self, data):
        eff = []
        from_pid = int(data.get('fromprofileid', 0))
        # Standard accept/decline response
        confirm = gs_query.create_gamespy_message([
             ('__cmd__', 'bm'), ('__cmd_val__', '1'),
             ('f', str(self.profileid)), ('msg', 'accepted')
        ])
        
        if self.context_provider and self.context_provider.get_active_profile(from_pid):
             eff.append(RouteEffect(from_pid, confirm.encode('latin-1')))
             
        # Pull mutual status update now established
        eff.extend(await self._yield_status_to_friends(from_pid))
        return eff

    # --- Status Routing Internal Builders ---
    
    async def _yield_status_to_friends(self, specific_buddy=None):
        """Internal implementation generating Status Relays to neighbors."""
        effects = []
        targets = [b for b in self.buddies if specific_buddy is None or b['buddyProfileId'] == int(specific_buddy)]
        
        for buddy in targets:
             target_id = buddy['buddyProfileId']
             
             # Fetch existing session data contextually from wrapper
             if not self.context_provider:
                 continue
                 
             partner = self.context_provider.get_active_profile(target_id)
             if partner and partner.get('gameid') == self.gameid:
                  # Construct outgoing status notice relay
                  stat_relay = gs_query.create_gamespy_message([
                       ('__cmd__', 'bm'), ('__cmd_val__', '100'),
                       ('f', str(self.profileid)),
                       ('msg', f"|s|{self.status}|ss|{self.statstring}|ls|{self.locstring}|ip|0|p|0")
                  ])
                  effects.append(RouteEffect(target_id, stat_relay.encode('latin-1')))
                  
                  # Also immediate return push of partner's state back to us (Synchronize state)
                  back_relay = gs_query.create_gamespy_message([
                       ('__cmd__', 'bm'), ('__cmd_val__', '100'),
                       ('f', str(target_id)),
                       ('msg', f"|s|{partner.get('status')}|ss|{partner.get('statstring')}|ls|{partner.get('locstring')}|ip|0|p|0")
                  ])
                  effects.append(ResponseEffect(back_relay.encode('latin-1')))
                  
        return effects
