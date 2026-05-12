import logging
import time
import traceback
from collections import namedtuple

import other.utils as utils
import gamespy.gs_utility as gs_utils

logger = logging.getLogger('GameSpyNatNegServer')

# Define explicit return payloads to remove coupling with transport writer methods
NatNegEffect = namedtuple('NatNegEffect', ['addr', 'data', 'delay'], defaults=[0])

class NatNegProtocol:
    """
    Handles the pure business logic and session mutations for NAT Negotiation packets.
    This is fully decoupled from threading and asyncio loops to satisfy SOLID principles
    and ease of unit testing.
    """
    MAGIC = bytearray([0xfd, 0xfc, 0x1e, 0x66, 0x6a, 0xb2])

    def __init__(self, server_data_resolver=None):
        self.session_list = {}
        self.natneg_preinit_session = {}
        self.server_data_resolver = server_data_resolver # Function or object that can query other servers list

        # Register command handlers mapping bytes to functions
        # Note Python 3 bytes indexing results in integers, so keys should be the integer values
        self.nn_commands = {
            0x00: self._handle_init,
            0x01: self._handle_initack,
            0x02: self._handle_erttest,
            0x03: self._handle_ertack,
            0x04: self._handle_stateupdate,
            0x05: self._handle_connect,
            0x06: self._handle_connect_ack,
            0x07: self._handle_connect_ping,
            0x08: self._handle_backup_test,
            0x09: self._handle_backup_ack,
            0x0A: self._handle_address_check,
            0x0B: self._handle_address_reply,
            0x0C: self._handle_natify_request,
            0x0D: self._handle_report,
            0x0E: self._handle_report_ack,
            0x0F: self._handle_preinit,
            0x10: self._handle_preinit_ack
        }

    def handle_packet(self, raw_data, addr):
        """
        Processes an incoming raw UDP packet, updates internal state, and yields Side Effects.
        Returns a list of NatNegEffect objects containing bytes and destination tuples.
        """
        effects = []
        
        # Validation check
        if not raw_data.startswith(self.MAGIC):
            logger.error("Dropped packet: Invalid MAGIC header from %s", addr)
            return effects
            
        if len(raw_data) < 8:
             logger.error("Dropped packet: Header too short from %s", addr)
             return effects
             
        command_opcode = raw_data[7]
        handler = self.nn_commands.get(command_opcode, self._handle_unknown)
        
        try:
            handler(raw_data, addr, effects)
        except Exception:
            logger.error("Failed processing NATNEG command 0x%02X from %s: %s", 
                         command_opcode, addr, traceback.format_exc())
                         
        return effects

    def _handle_unknown(self, recv_data, addr, effects):
        logger.debug("Received unknown NATNEG command 0x%02X from %s", recv_data[7], addr)

    def _handle_init(self, recv_data, addr, effects):
        """Command: 0x00 - NN_INIT."""
        logger.debug("Received initialization from %s:%d...", *addr)
        
        session_id = utils.get_int(recv_data, 8)
        output = bytearray(recv_data[0:14])
        
        # Standardization response marker
        output += bytearray([0xff, 0xff, 0x6d, 0x16, 0xb5, 0x7d, 0xea])
        output[7] = 0x01 # INITACK
        effects.append(NatNegEffect(addr, bytes(output)))
        
        # Session mapping
        gameid = utils.get_string(recv_data, 0x15)
        client_id = "%02x" % recv_data[13]
        localaddr = utils.get_local_addr(recv_data, 15)
        
        self.session_list.setdefault(session_id, {}).setdefault(client_id, {
            'connected': False,
            'addr': '',
            'localaddr': None,
            'serveraddr': None,
            'gameid': None
        })
        
        client_id_session = self.session_list[session_id][client_id]
        client_id_session['gameid'] = gameid
        client_id_session['addr'] = addr
        client_id_session['localaddr'] = localaddr
        
        # Attempt cross-matching other peer in this session
        for other_client_id in list(self.session_list[session_id].keys()):
            client_session = self.session_list[session_id][other_client_id]
            if client_session['connected'] or other_client_id == client_id:
                continue
                
            # Resolver injection used to pull outside global knowledge without coupling networking
            if self.server_data_resolver:
                serveraddr = self.server_data_resolver(gameid, session_id, other_client_id, self.session_list)
                client_session['serveraddr'] = serveraddr
                
                rev_serveraddr = self.server_data_resolver(gameid, session_id, client_id, self.session_list)
                client_id_session['serveraddr'] = rev_serveraddr
            
            # Construct peer cross-connect packet to requester
            pubport_peer = int(client_session['serveraddr']['publicport']) if client_session.get('serveraddr') else \
                           (client_session['localaddr'][1] or client_session['addr'][1])
                           
            peer_pkt = bytearray(recv_data[0:12])
            peer_pkt += utils.get_bytes_from_ip_str(client_session['addr'][0])
            peer_pkt += utils.get_bytes_from_short(pubport_peer, True)
            peer_pkt += bytearray([0x42, 0x00])
            peer_pkt[7] = 0x05 # NN_CONNECT
            effects.append(NatNegEffect(client_id_session['addr'], bytes(peer_pkt)))
            
            # Construct back-connect packet to original peer
            pubport_self = int(client_id_session['serveraddr']['publicport']) if client_id_session.get('serveraddr') else \
                           (client_id_session['localaddr'][1] or client_id_session['addr'][1])
                           
            self_pkt = bytearray(recv_data[0:12])
            self_pkt += utils.get_bytes_from_ip_str(client_id_session['addr'][0])
            self_pkt += utils.get_bytes_from_short(pubport_self, True)
            self_pkt += bytearray([0x42, 0x00])
            self_pkt[7] = 0x05 # NN_CONNECT
            effects.append(NatNegEffect(client_session['addr'], bytes(self_pkt)))

    def _handle_initack(self, recv_data, addr, effects):
        logger.warning("Received client unexpected INITACK command from %s", addr)

    def _handle_erttest(self, recv_data, addr, effects):
        logger.warning("Received client unexpected ERTTEST command from %s", addr)

    def _handle_ertack(self, recv_data, addr, effects):
        logger.info("Received ERT acknowledgement from %s", addr)

    def _handle_stateupdate(self, recv_data, addr, effects):
        logger.warning("Received unimplemented STATEUPDATE from %s", addr)

    def _handle_connect(self, recv_data, addr, effects):
         logger.warning("Received client unexpected CONNECT command from %s", addr)

    def _handle_connect_ack(self, recv_data, addr, effects):
        """Command 0x06 - Connect acknowledged by client."""
        client_id = "%02x" % recv_data[13]
        session_id = utils.get_int(recv_data, 8)
        logger.debug("Session connection ack from %s", addr)
        if session_id in self.session_list and client_id in self.session_list[session_id]:
            self.session_list[session_id][client_id]['connected'] = True

    def _handle_connect_ping(self, recv_data, addr, effects):
        logger.warning("Received peer direct ping leak packet from %s", addr)

    def _handle_backup_test(self, recv_data, addr, effects):
        logger.debug("Backup command from %s", addr)
        out = bytearray(recv_data)
        out[7] = 0x09 # BACKUP_ACK
        effects.append(NatNegEffect(addr, bytes(out)))

    def _handle_backup_ack(self, recv_data, addr, effects):
        logger.warning("Received server BACKUP_ACK from client %s", addr)

    def _handle_address_check(self, recv_data, addr, effects):
        """Command 0x0A - Reflection mechanism."""
        logger.debug("Received address check from %s", addr)
        out = bytearray(recv_data[0:15])
        out += utils.get_bytes_from_ip_str(addr[0])
        out += utils.get_bytes_from_short(addr[1], True)
        out += bytearray(recv_data[len(out):])
        out[7] = 0x0B # ADDRESS_REPLY
        effects.append(NatNegEffect(addr, bytes(out)))

    def _handle_address_reply(self, recv_data, addr, effects):
        logger.warning("Received server ADDRESS_REPLY from client %s", addr)

    def _handle_natify_request(self, recv_data, addr, effects):
        logger.debug("Natify received from %s", addr)
        out = bytearray(recv_data)
        out[7] = 0x02 # ERTTEST response
        effects.append(NatNegEffect(addr, bytes(out)))

    def _handle_report(self, recv_data, addr, effects):
        logger.debug("Received client stats report from %s", addr)
        out = bytearray(recv_data[:21])
        out[7] = 0x0E # REPORTACK
        out[14] = 0
        effects.append(NatNegEffect(addr, bytes(out)))

    def _handle_report_ack(self, recv_data, addr, effects):
        logger.warning("Received server REPORT_ACK from client %s", addr)

    def _handle_preinit(self, recv_data, addr, effects):
        """Command 0x0F - Special Pokemon setup handler."""
        logger.debug("Preinit packet from %s", addr)
        session = utils.get_int(recv_data[-4:], 0)
        
        out = bytearray(recv_data[:-4]) + bytearray([0,0,0,0])
        out[7] = 0x10 # PREINIT_ACK
        
        if not session:
            out[13] = 2
        elif session in self.natneg_preinit_session:
            out[13] = 2
            effects.append(NatNegEffect(self.natneg_preinit_session[session], bytes(out)))
            
            # Construct back to other party
            alt_out = bytearray(out)
            alt_out[12] = 1 if alt_out[12] == 0 else 0
            effects.append(NatNegEffect(addr, bytes(alt_out)))
            
            del self.natneg_preinit_session[session]
            return # already generated explicit response effects
        else:
            out[13] = 0
            self.natneg_preinit_session[session] = addr
            
        effects.append(NatNegEffect(addr, bytes(out)))

    def _handle_preinit_ack(self, recv_data, addr, effects):
         logger.warning("Received server PREINIT_ACK from client %s", addr)
