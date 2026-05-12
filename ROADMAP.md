# Project Sovereign Roadmap

## Phase 1: Codebase Eradication & Data Modernization
The original repository relies on `SocketServer` threading and file-based SQLite locks, which will mathematically fail under concurrent load. We fix the data layer first.

### Step 1: Python 3 & asyncio Overhaul
* **The Technical Work:** The current `master_server.py` spawns synchronous threads for every connection. Rewrite the core networking loops in `gamespy_profile_server.py` and `gamespy_natneg_server.py` using Python 3.12’s `asyncio.DatagramProtocol` for UDP and `asyncio.start_server` for TCP.
* **Specific Result:** A single Raspberry Pi core can now process thousands of concurrent GameSpy packets asynchronously without thread-locking or memory leaks.

### Step 2: Database Migration (SQLite to PostgreSQL)
* **The Technical Work:** Rip out the `sqlite3` imports in `gamespy/gs_database.py` and `other/sql.py`. Stand up a PostgreSQL instance. Rewrite the SQL queries using a modern async driver like `asyncpg` to utilize connection pooling.
* **Specific Result:** Complete elimination of "database is locked" errors during peak matchmaking. Read/write operations (like logging stats or verifying profiles) are now handled concurrently.

### Step 3: Redis Ephemeral State Manager
* **The Technical Work:** Implement Redis to handle the volatile network states. When a Wii sends a packet to `gamespy_server_browser_server.py`, store the session key and IP in Redis with a 30-second Time-To-Live (TTL). Each heartbeat resets the TTL.
* **Specific Result:** Fixes the infamous Error 52200. Ghost lobbies are automatically destroyed by Redis the exact moment a player's Wi-Fi drops, preventing stale socket crashes.

---

## Phase 2: Architectural Deconstruction & Edge Orchestration
We tear apart the monolithic script into isolated, self-healing microservices managed by local Kubernetes.

### Step 4: Microservices Breakout
* **The Technical Work:** Delete `master_server.py` entirely. Write distinct `Dockerfiles` for each protocol:
  * `nas_container` (Port 80/TCP - Login)
  * `profile_container` (Port 29900/TCP - Accounts)
  * `natneg_container` (Port 27901/UDP - Matchmaking)
* **Specific Result:** Strict fault isolation. If a malformed packet crashes the profile container, active matches running on the NatNeg container survive seamlessly.

### Step 5: Kubernetes (K3s) Edge Deployment
* **The Technical Work:** Write Kubernetes `deployment.yaml` and `service.yaml` manifests. Use K3s (a lightweight K8s binary optimized for IoT/ARM architectures like a Raspberry Pi) to orchestrate the Docker containers into unified Pods.
* **Specific Result:** Automated self-healing. K3s monitors the microservices and restarts any crashed containers in milliseconds without user intervention.

### Step 6: Layer 7 API Gateway
* **The Technical Work:** Deploy Traefik or NGINX Ingress inside the K3s cluster to bind to TCP Port 80. Configure HTTP routing rules based on the `Host` header.
* **Specific Result:** Extensibility. Traffic hitting `naswii.nintendowifi.net` routes to the legacy NAS container, but you now have the architecture to route `gamestats.gs.nintendowifi.net` to entirely new, custom microservices in the future.

---

## Phase 3: The Security Perimeter & Access Layer
Exposing legacy emulation protocols to the open internet is a critical security vulnerability. We build a zero-trust cryptographic boundary.

### Step 7: The GameSpy DPI Proxy (C Programming)
* **The Technical Work:** Do not let internet traffic touch the Python containers directly. Write a high-performance Deep Packet Inspection (DPI) proxy in C. Have this proxy bind to the raw UDP ports. It inspects the hex payloads, verifying the proprietary Nintendo null-terminated (`\x00`) string structures.
* **Specific Result:** A custom Web Application Firewall (WAF) for retro games. It instantly drops buffer-overflow attempts and automated port scanners, passing only strictly sanitized GameSpy packets to the Python backend.

### Step 8: Automated WireGuard Gateway
* **The Technical Work:** Deploy the `wg-easy` Docker image as a privileged sidecar Pod in K3s. The Host opens a single port on their router (UDP 51820).
* **Specific Result:** Sovereign, zero-cost remote access. The Host generates client configs in a web UI. Friends drop the config into the official WireGuard app and connect instantly. Zero limits on player count, bypassing commercial VPN restrictions.

---

## Phase 4: Observability, CI/CD, & UX
We make the infrastructure visible and build the tools required for non-technical friends to actually use it.

### Step 9: SRE Observability Stack
* **The Technical Work:** Integrate the `prometheus_client` library into your Python microservices to export telemetry (active players, packet latency). Deploy Prometheus and Grafana into the K3s cluster.
* **Specific Result:** A live, dark-mode web dashboard running on the Pi. The server Host can visually monitor database health, active matches, and network throughput in real-time.

### Step 10: "1-Click" Patcher Portal (TypeScript/React)
* **The Technical Work:** Build a local web portal using Next.js/React. Expose an API endpoint that triggers the `nossl_patch_arm9.c` binary (found in the original repo's `tools` folder) against uploaded files.
* **Specific Result:** Zero terminal work for friends. They access your portal via browser, upload their legally dumped `.iso`, and the backend automatically mutates the binary to strip SSL and injects the WireGuard DNS, instantly returning a playable game file.