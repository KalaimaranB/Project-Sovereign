"""DWC Network Server Emulator - Fixed NAS Server

Fixes:
- conntest now handles /conntest/main.html path that Nintendo consoles request
- Proper response headers for conntest
"""

import logging
import time
import http.server as BaseHTTPServer
import socketserver as SocketServer
import traceback
import threading
import asyncio
import os

from other import metrics
from gamespy.pg_database_sync import PostgresGamespyDatabaseSync
from other import utils
import dwc_config

logger = dwc_config.get_logger('NasServer')


def handle_post(handler, addr, post):
    """Handle unknown path."""
    logger.log(logging.WARNING, "Unknown path request %s from %s:%d!",
               handler.path, *addr)
    handler.send_response(404)
    return None


def handle_ac_action(handler, db, addr, post):
    """Handle unknown ac action request."""
    logger.log(logging.WARNING, "Unknown ac action: %s", handler.path)
    return {}


def handle_ac_acctcreate(handler, db, addr, post):
    """Handle ac acctcreate request."""
    if db.is_banned(post):
        ret = {
            "retry": "1",
            "returncd": "3913",
            "locator": "gamespy.com",
            "reason": "User banned."
        }
        logger.log(logging.DEBUG, "Acctcreate denied for banned user %s", str(post))
    else:
        ret = {
            "retry": "0",
            "returncd": "002",
            "userid": db.get_next_available_userid()
        }
        logger.log(logging.DEBUG, "Acctcreate response to %s:%d", *addr)
        logger.log(logging.DEBUG, "%s", ret)
    return ret


def handle_ac_login(handler, db, addr, post):
    """Handle ac login request."""
    if db.is_banned(post):
        ret = {
            "retry": "1",
            "returncd": "3914",
            "locator": "gamespy.com",
            "reason": "User banned."
        }
        logger.log(logging.DEBUG, "Login denied for banned user %s", str(post))
    else:
        challenge = utils.generate_random_str(8)
        post["challenge"] = challenge
        authtoken = db.generate_authtoken(post["userid"], post)
        ret = {
            "retry": "0",
            "returncd": "001",
            "locator": "gamespy.com",
            "challenge": challenge,
            "token": authtoken,
        }
        logger.log(logging.DEBUG, "Login response to %s:%d", *addr)
        logger.log(logging.DEBUG, "%s", ret)
    return ret


def handle_ac_svcloc(handler, db, addr, post):
    """Handle ac svcloc request."""
    ret = {
        "retry": "0",
        "returncd": "007",
        "statusdata": "Y"
    }
    authtoken = db.generate_authtoken(post["userid"], post)

    if 'svc' in post:
        if post["svc"] in ("9000", "9001"):
            svchost = dwc_config.get_svchost('NasServer')
            ret["svchost"] = svchost if svchost else handler.headers['host']
            ret["svchost"] = ret["svchost"].split(',')[0]
            if post["svc"] == "9000":
                ret["token"] = authtoken
            else:
                ret["servicetoken"] = authtoken
        elif post["svc"] == "0000":
            ret["servicetoken"] = authtoken
            ret["svchost"] = "n/a"
        else:
            ret["svchost"] = "n/a"
            ret["servicetoken"] = authtoken

    logger.log(logging.DEBUG, "Svcloc response to %s:%d", *addr)
    logger.log(logging.DEBUG, "%s", ret)
    return ret


def handle_ac(handler, addr, post):
    """Handle ac POST request."""
    logger.log(logging.DEBUG, "Ac request to %s from %s:%d",
               handler.path, *addr)
    logger.log(logging.DEBUG, "%s", post)

    action_bytes = post.get("action", b"")
    action = action_bytes.decode('latin-1').lower() if isinstance(action_bytes, bytes) else str(action_bytes).lower()
    command = handler.ac_actions.get(action, handle_ac_action)
    ret = command(handler, handler.server.db, addr, post)

    ret.update({"datetime": time.strftime("%Y%m%d%H%M%S")})
    handler.send_response(200)
    handler.send_header("Content-type", "text/plain")
    handler.send_header("NODE", "wifiappe1")

    return utils.dict_to_qs(ret)


def handle_pr(handler, addr, post):
    """Handle pr POST request."""
    logger.log(logging.DEBUG, "Pr request to %s from %s:%d",
               handler.path, *addr)
    logger.log(logging.DEBUG, "%s", post)

    words = len(post["words"].split('\t'))
    wordsret = "0" * words
    ret = {
        "prwords": wordsret,
        "returncd": "000",
        "datetime": time.strftime("%Y%m%d%H%M%S")
    }

    for l in "ACEJKP":
        ret["prwords" + l] = wordsret

    handler.send_response(200)
    handler.send_header("Content-type", "text/plain")
    handler.send_header("NODE", "wifiappe1")

    logger.log(logging.DEBUG, "Pr response to %s:%d", *addr)
    logger.log(logging.DEBUG, "%s", ret)

    return utils.dict_to_qs(ret)


class NasHTTPServerHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """Nintendo NAS server handler."""

    post_paths = {
        "/ac": handle_ac,
        "/pr": handle_pr,
    }

    ac_actions = {
        "acctcreate": handle_ac_acctcreate,
        "login": handle_ac_login,
        "svcloc": handle_ac_svcloc,
    }

    def version_string(self):
        return "Nintendo Wii (http)"

    def log_message(self, format, *args):
        # Route to our logger instead of stderr
        logger.log(logging.DEBUG, "%s - - [%s] %s",
                   self.address_string(),
                   self.log_date_time_string(),
                   format % args)

    def do_GET(self):
        """Handle GET request.

        Nintendo DS/Wii connectivity test hits:
          - conntest.nintendowifi.net/  (bare root)
          - conntest.nintendowifi.net/conntest/main.html  (Wii)
          - naswii.nintendowifi.net/  (bare root, Wii)

        All must return HTTP 200 with body "ok" to pass the internet check.
        """
        try:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.send_header("X-Organization", "Nintendo")
            self.send_header("Server", "BigIP")
            self.end_headers()
            self.wfile.write(b"ok")
            metrics.record_http_request('nas', 'GET conntest', 200)
            logger.log(logging.DEBUG, "Conntest GET %s from %s",
                       self.path, self.client_address[0])
        except Exception:
            logger.log(logging.ERROR, "Exception occurred on GET request!")
            logger.log(logging.ERROR, "%s", traceback.format_exc())

    def do_POST(self):
        try:
            length = int(self.headers['content-length'])
            post = utils.qs_to_dict(self.rfile.read(length))
            client_address = (
                self.headers.get('x-forwarded-for', self.client_address[0]),
                self.client_address[1]
            )
            post['ipaddr'] = client_address[0]

            command = self.post_paths.get(self.path, handle_post)
            ret = command(self, client_address, post)

            if ret is not None:
                if isinstance(ret, str):
                    ret = ret.encode('latin-1')
                self.send_header("Content-Length", str(len(ret)))
                self.end_headers()
                self.wfile.write(ret)

            status = 200 if ret is not None else 404
            metrics.record_http_request('nas', 'POST ' + self.path, status)
        except Exception:
            logger.log(logging.ERROR, "Exception occurred on POST request!")
            logger.log(logging.ERROR, "%s", traceback.format_exc())


class NasHTTPServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    """Threading HTTP server with dedicated bridge backend."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = PostgresGamespyDatabaseSync()


class NasServer(object):
    def start(self):
        metrics_port = int(os.environ.get('METRICS_PORT', 9102))
        metrics.launch_metrics_endpoint(metrics_port)

        address = dwc_config.get_ip_port('NasServer')
        httpd = NasHTTPServer(address, NasHTTPServerHandler)
        logger.log(logging.INFO, "Now listening for connections on %s:%d...",
                   *address)
        httpd.serve_forever()


if __name__ == "__main__":
    nas = NasServer()
    nas.start()