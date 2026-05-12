"""Sovereign ROM Patcher API Microservice

   A lightweight HTTP server facilitating the "Zero Terminal" ROM patching experience.
   Accepts user ROM files, triggers the compiled C binary for byte replacement,
   and streams the result back to the React dashboard instantly.
"""

import http.server
import socketserver
import os
import subprocess
import tempfile
import cgi
import sys

import dwc_config

logger = dwc_config.get_logger('PatcherServer')

# Fallback port in case dwc_config does not explicitly map PatcherServer
PORT = 9999

class PatcherAPIHandler(http.server.BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Requested-With')

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_POST(self):
        if self.path != '/api/patch':
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()
            return

        try:
            ctype, pdict = cgi.parse_header(self.headers.get('content-type'))
            
            # Ensure boundaries are parsed correctly for binary stability
            if 'boundary' in pdict:
                if isinstance(pdict['boundary'], str):
                    pdict['boundary'] = pdict['boundary'].encode('ascii')

            if ctype != 'multipart/form-data':
                self.send_response(400)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(b"Error: Request must be multipart/form-data")
                return

            # Handle multipart form variables
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST',
                         'CONTENT_TYPE': self.headers['content-type']}
            )

            if 'rom' not in form or 'ip' not in form:
                self.send_response(400)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(b"Error: Missing 'rom' file or 'ip' parameter in payload")
                return

            file_item = form['rom']
            ip_value = form.getfirst('ip')

            if not file_item.file:
                self.send_response(400)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(b"Error: No ROM data uploaded.")
                return

            original_filename = file_item.filename if file_item.filename else "patched_rom.nds"
            logger.info(f"Received patch request for {original_filename}, replacing 'nintendowifi.net' -> '{ip_value}'")

            # Generate safe, temporary I/O files for the subprocess stream
            with tempfile.NamedTemporaryFile(delete=False) as temp_in:
                temp_in_path = temp_in.name
                # Read block-by-block to prevent RAM explosion on big ISOs
                while True:
                    chunk = file_item.file.read(1024 * 1024) # 1MB chunks
                    if not chunk:
                        break
                    temp_in.write(chunk)

            temp_out_path = temp_in_path + "_patched"

            try:
                # Dynamically find patcher binary inside the execution context
                binary_path = os.path.join(os.path.dirname(__file__), '../tools/sovereign_patcher')
                if not os.path.exists(binary_path):
                    # Fallback for container layout
                    binary_path = '/app/tools/sovereign_patcher'

                logger.info(f"Invoking patcher utility: {binary_path}")

                # Trigger C binary replacement: target static domain -> User Wireguard/Host IP
                cmd = [
                    binary_path,
                    temp_in_path,
                    temp_out_path,
                    "nintendowifi.net",
                    ip_value
                ]
                
                process = subprocess.run(cmd, capture_output=True, text=True)

                if process.returncode != 0:
                    logger.error(f"C-Patcher Execution Failed: {process.stderr}")
                    self.send_response(500)
                    self.send_cors_headers()
                    self.end_headers()
                    self.wfile.write(f"Internal Patcher Error:\n{process.stderr}".encode())
                    return

                logger.info(f"C-Patcher finished successfully:\n{process.stdout}")

                if not os.path.exists(temp_out_path):
                    raise FileNotFoundError("Patched output binary missing post-compilation execution!")

                # Stream output file directly to browser
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Disposition', f'attachment; filename="patched_{original_filename}"')
                self.send_cors_headers()
                
                file_size = os.path.getsize(temp_out_path)
                self.send_header('Content-Length', str(file_size))
                self.end_headers()

                with open(temp_out_path, 'rb') as f:
                    while True:
                        chunk = f.read(1024 * 1024)
                        if not chunk:
                            break
                        self.wfile.write(chunk)

                logger.info(f"Successfully delivered patched_{original_filename} to client.")

            finally:
                # Clean up temporary binary buffers immediately
                for path in (temp_in_path, temp_out_path):
                    if os.path.exists(path):
                        os.remove(path)

        except Exception as e:
            logger.exception(f"Unexpected error handling ROM patch endpoint: {e}")
            self.send_response(500)
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(f"Server Error: {str(e)}".encode())

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

def start_server():
    server_address = ('', PORT)
    httpd = ThreadedHTTPServer(server_address, PatcherAPIHandler)
    logger.info(f"Sovereign ROM Patcher API listening on 0.0.0.0:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

if __name__ == "__main__":
    start_server()
