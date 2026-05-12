# 🛠️ Project Sovereign Operations Manual

This guide provides complete administrative and engineering instructions for deploying, developing, and operationalizing the Project Sovereign emulation stack.

---

## 🧪 Section 1: Local Development & Test Execution

To edit the codebase or verify changes safely outside of containerized layers, you should utilize the localized virtual environment.

### 1. Environment Bootstrap
```bash
# 1. Generate isolated Python context
python -m venv venv
source venv/bin/activate

# 2. Install dependency catalog
pip install -r requirements.txt
```

### 2. The Test Matrix (`pytest`)
We enforce rigorous unit and behavioral coverage across the entire stack. Execute standard testing via:
```bash
pytest
```
To monitor stdout printouts during individual test failures, execute with verbose flags:
```bash
pytest -vv -s
```

---

## 🐳 Section 2: Multi-Container Docker Operations

Production environments utilize Docker Compose to orchestrate database pools, Redis caching, and the Python application network.

### 📑 Fundamental Command Reference

| Objective | Shell Instruction |
|-----------|-------------------|
| **Launch Mesh** | `docker compose up -d` |
| **Rebuild & Launch** | `docker compose up -d --build` |
| **Stop Entire Stack** | `docker compose down` |
| **Check Pod States** | `docker compose ps` |
| **View Daemon Logs** | `docker compose logs -f [container_name]` |

### 📊 Accessing Running Containers
To directly access the running PostgreSQL instance to inspect live table data:
```bash
docker compose exec sovereign_db psql -U dwc_admin -d gamespy
```

To monitor Redis dynamic cache insertions in real-time:
```bash
docker compose exec sovereign_redis redis-cli MONITOR
```

---

## 🌐 Section 3: Network Topology & Console DNS Routing

For a physical Nintendo DS or Wii console to connect to your Project Sovereign instance, you must redirect GameSpy domain requests to your host machine's IP address.

### 🗺️ Required Domain Redirect Vectors
Configure your local DNS server (e.g., Pi-hole, BIND, or Dnsmasq) to resolve the following wildcard and root domains to your **Docker Host LAN IP**:

```text
# Wi-Fi Connection Base Login
naswii.nintendowifi.net -> [YOUR_SERVER_IP]
conntest.nintendowifi.net -> [YOUR_SERVER_IP]

# Master Server Search & Query
*.available.gs.nintendowifi.net -> [YOUR_SERVER_IP]
*.master.gs.nintendowifi.net -> [YOUR_SERVER_IP]
*.ms.nintendowifi.net -> [YOUR_SERVER_IP]

# Accounts & Stats Engines
gpcm.gs.nintendowifi.net -> [YOUR_SERVER_IP]
gpsp.gs.nintendowifi.net -> [YOUR_SERVER_IP]
gamestats.gs.nintendowifi.net -> [YOUR_SERVER_IP]
sake.gs.nintendowifi.net -> [YOUR_SERVER_IP]
```

---

## 📊 Section 4: Server Monitoring & Administration

Project Sovereign provides native administrative control planes and telemetry layers to observe server health.

### 1. The Administration Panel
The Admin control plane resides on standard HTTP interface.
- **Access URL:** [http://localhost:9009](http://localhost:9009)
- **Capabilities:**
  - **MAC Whitelisting:** Approve console hardware IDs currently sitting in the `pending` ledger.
  - **Blacklist Engine:** Directly ban abusive or misconfigured remote IP addresses and Game IDs.

### 2. Observability & Telemetry Exporters
Microservices export standard Prometheus metrics to visual dashboards.
- **Endpoint Port:** `9101` (Standard for metrics exposition)
- **Key Metrics Published:**
  - `sovereign_packets_received_total`: Counter tracking QR & NatNeg opcodes handled.
  - `sovereign_database_query_duration_seconds`: Histogram measuring connection pool query latencies.

---

## 📡 Section 5: Zero-Trust Remote Play via WireGuard

To allow friends outside your local network to safely play retro games without port-forwarding insecure Nintendo ports, Project Sovereign includes a high-performance **WireGuard VPN Gateway** (`wg-easy`).

### 1. Initial Configuration
Before launching, update your public IP or Dynamic DNS in `docker-compose.yml`:
```yaml
sovereign_vpn:
  environment:
    - WG_HOST=your_public_ip_or_ddns.com  # Replace with your WAN IP or Hostname
    - PASSWORD=your_custom_admin_pass     # Replace with a strong dashboard password
```

### 2. Launch and Firewall Rules
Ensure your home router forwards **UDP Port 51820** to your Docker host IP. This is the *only* port your router needs to open to the internet!

Launch the VPN stack:
```bash
docker compose up -d sovereign_vpn
```

### 3. Generating Friendly Clients via Web GUI
Project Sovereign exposes a gorgeous dark-mode VPN UI to manage connected peers easily.

1. Navigate to the Admin UI in your browser: **[http://localhost:51821](http://localhost:51821)**
2. Authenticate using your configured `PASSWORD`.
3. Click **+ New Client** and enter your friend's username (e.g., `alice_ds`).
4. **Onboarding options:**
   - 📲 **Show QR Code:** Alice opens the WireGuard Mobile app (iOS/Android), taps `+`, scans the QR code, and connects instantly!
   - 📥 **Download Profile:** Send Alice the generated `.conf` file to import directly into the official WireGuard Windows/Mac/Linux client.

### 4. Secure Handshakes
Once connected, your friend's device enters the secure Docker container mesh (`10.8.0.0/24`). Their GameSpy domain traffic resolves internally directly to your microservices, entirely bypassing the public internet with enterprise-grade ChaCha20-Poly1305 cryptography!
