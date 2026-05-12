# 🕹️ Project Sovereign

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![PostgreSQL 16](https://img.shields.io/badge/database-PostgreSQL_16-purple.svg)](https://www.postgresql.org/)
[![Docker Ready](https://img.shields.io/badge/docker-compose-green.svg)](https://www.docker.com/)
[![Testing Suite](https://img.shields.io/badge/tests-39%2F39%20passed-brightgreen.svg)](file:///Users/kalaimaranbalasothy/GitHub%20Projects/Project%20Sovereign/tests)

A state-of-the-art, high-performance Nintendo DS and Wii online multiplayer server emulator. Engineered for absolute concurrency, sub-millisecond latency, and zero-trust resilience.

Project Sovereign is a modern overhaul of the legacy Nintendo Wi-Fi Connection (WFC) stack, translating procedural, single-threaded architectures into a containerized, self-healing microservice ecosystem.

---

## 🌟 Modern Engineering Enhancements

*   🚀 **Pure Python 3.13 & AsyncIO:** Eradicated legacy `SocketServer` threading. High-traffic UDP/TCP listeners (QR and NatNeg) utilize asynchronous event loops, capable of serving thousands of players on a single-core processor.
*   🐘 **Native PostgreSQL Vector:** Fully excised vestigial, file-locking `sqlite3` databases. Operations utilize persistent connection pooling and dynamic ANSI Information Schema catalog lookups.
*   ⚡ **Redis Ephemeral State Management:** Active multiplayer lobbies, server heartbeats, and short-lived matchmaking sessions utilize Redis caching with TTL expirations, preventing the infamous stale socket "Error 52200".
*   🏗️ **Clean Microservice Topology:** The codebase is fully structured as an import-safe python package. Consolidates independent service entrypoints inside `services/` and centralized configuration templates inside `config/`.
*   📈 **Telemetry & Dashboards:** Native metrics extraction integrating standard HTTP exporter endpoints, tracking active players, database queries, and packet latencies in real-time.
*   🛡️ **Enterprise C Security Perimeter:** High-speed GameSpy UDP boundaries are shielded by a custom Web Application Firewall written in C, executing non-blocking Deep Packet Inspection (DPI) to instantly drop malformed scanner probes and binary overflows.
*   📡 **Zero-Trust Remote VPN Gateway:** Native, integrated WireGuard (`wg-easy`) providing an automated, dark-mode Web UI to seamlessly generate secure QR-code entry keys for external friends, ensuring total packet isolation.

---

## 🚀 60-Second Quick Start

Ensure you have [Docker](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/) installed.

1.  **Clone & Launch the Stack:**
    ```bash
    docker compose up -d --build
    ```
2.  **Verify Running Daemons:**
    ```bash
    docker compose ps
    ```
3.  **Access the Web Admin:**
    Open [http://localhost:9009](http://localhost:9009) in your browser to manage registered MAC addresses and check bans.

---

## 📚 The Handbook

Explore our deep-dive technical documentation inside the [/docs](file:///Users/kalaimaranbalasothy/GitHub%20Projects/Project%20Sovereign/docs) directory:

*   💡 **[Getting Started Guide](file:///Users/kalaimaranbalasothy/GitHub%20Projects/Project%20Sovereign/docs/GETTING_STARTED.md):** The absolute entry-point for new server operators, taking you from zero to hosting lobbies in under 5 minutes.
*   📚 **[Technical Knowledge Base](file:///Users/kalaimaranbalasothy/GitHub%20Projects/Project%20Sovereign/docs/README.md):** Glorious Master Architecture maps and 11 dedicated protocol blueprints detailing precise packet hex/ASCII structures for all running servers.
*   📖 **[Operations Manual](file:///Users/kalaimaranbalasothy/GitHub%20Projects/Project%20Sovereign/docs/OPERATIONS.md):** Step-by-step guide on local virtualenv setups, executing unit tests, orchestrating Docker deployments, and routing retro console DNS.
*   🏗️ **[System Architecture](file:///Users/kalaimaranbalasothy/GitHub%20Projects/Project%20Sovereign/docs/ARCHITECTURE.md):** Complete breakdown of the microservice orchestration layers and network telemetry maps.
*   🐘 **[Database Schema](file:///Users/kalaimaranbalasothy/GitHub%20Projects/Project%20Sovereign/docs/DATABASE_SCHEMA.md):**Authoritative reference mapping table structures, unique atomic indices, and persistence logic.
*   🧬 **[Protocol Internals](file:///Users/kalaimaranbalasothy/GitHub%20Projects/Project%20Sovereign/docs/PROTOCOL_INTERNALS.md):** Detailed breakdown explaining how proprietary GameSpy RC4 challenges, UDP stateful reflection, and dynamic Sake storage work under the hood.

---

## 🧪 Local Development & Testing

For active development, establish a standard Python local virtualenv:

```bash
# 1. Establish Virtualenv
python -m venv venv
source venv/bin/activate

# 2. Install Dependencies
pip install -r requirements.txt

# 3. Execute the Global Testing Matrix
pytest
```

We maintain a **strict 100% pass standard** across 39+ unified test vectors covering Database Sync drivers, Redis TTL caching, and server handler mocks.
