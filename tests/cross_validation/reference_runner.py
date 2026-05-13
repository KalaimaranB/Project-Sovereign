import subprocess
import time
import requests
import socket

class ReferenceEmulator:
    def __init__(self, port_mapping=None):
        self.container_id = None
        self.port_mapping = port_mapping or {
            9000: 9000,   # NAS
            28910: 28910, # Browser
            29900: 29900, # Profile
        }
        
    def start(self):
        # Build the image if not already built
        subprocess.run(
            ["docker", "build", "-t", "sovereign-reference:latest", "-f", "tests/cross_validation/Dockerfile.reference", "tests/cross_validation/"],
            check=True,
            capture_output=True
        )
        
        # Ensure no zombie container is taking the port
        subprocess.run(["docker", "rm", "-f", "sovereign-ref"], check=False, capture_output=True)
        
        # Start the container
        cmd = ["docker", "run", "-d", "--name", "sovereign-ref"]
        for host_port, cont_port in self.port_mapping.items():
            cmd.extend(["-p", f"{host_port}:{cont_port}"])
        cmd.append("sovereign-reference:latest")
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        self.container_id = result.stdout.strip()
        
        # Wait for the HTTP server to come up (e.g. NAS)
        host_port = next((host for host, cont in self.port_mapping.items() if cont == 9000), None)
        if host_port:
            self._wait_for_port(host_port)
        time.sleep(1) # Extra settling time

    def stop(self):
        if self.container_id:
            subprocess.run(["docker", "stop", self.container_id], check=False, capture_output=True)
            self.container_id = None
            
    def _wait_for_port(self, port, timeout=10):
        start = time.time()
        while time.time() - start < timeout:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=1):
                    return
            except OSError:
                time.sleep(0.5)
        raise TimeoutError(f"Container failed to bind port {port} within {timeout}s")
