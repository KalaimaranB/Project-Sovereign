# 🏗️ Project Sovereign Cluster Architecture

This document visualizes and defines the high-availability, containerized microservice ecosystem deployed in **Phase 2** orchestrations.

## 🗺️ System Map

```mermaid
graph TD
    subgraph "External Network (Wii / Consoles)"
        WII[Nintendo Wii Client]
    end

    subgraph "Sovereign Edge Gateway"
        LB_NAS[LoadBalancer Port 9000]
        LB_QR[LoadBalancer Port 27900 UDP]
        LB_PROF[LoadBalancer Port 29900]
    end

    subgraph "Self-Healing Application Pods (Python 3.13)"
        NAS[sovereign-nas]
        QR[sovereign-qr]
        PROF[sovereign-profile]
    end

    subgraph "Core Persistence Mesh (Stateful)"
        DB[(PostgreSQL)]
        RED[(Redis Cache)]
    end

    %% Traffic Flows
    WII -->|HTTP Login| LB_NAS
    WII -->|UDP Stats| LB_QR
    WII -->|TCP Accounts| LB_PROF

    LB_NAS --> NAS
    LB_QR --> QR
    LB_PROF --> PROF

    %% Backend Persistence Links
    NAS -->|asyncpg| DB
    QR -->|asyncpg| DB
    QR -->|redis-py| RED
    PROF -->|asyncpg| DB
```

## 🧬 Core Principles

### 1. Immutable Containerization
All application code runs within an immutable Python 3.13 hardened base image (`Dockerfile`). Overriding `command` parameters in Docker Compose / K8s enables absolute image reuse across disparate daemon types, guaranteeing 100% execution environment parity.

### 2. The Self-Healing Paradigm
Unlike the legacy `master_server.py` monolith where a single python runtime crash would collapse all services, Project Sovereign treats each daemon as a managed resource. If `sovereign-qr` undergoes a fatal exception, the orchestration layer instantaneously resurrects the standalone container in milliseconds without disrupting existing HTTP login threads.

### 3. Zero-Touch Service Discovery
Services dynamically interrogate the ambient execution environment for `DATABASE_URL` and `REDIS_URL`. 
- **Docker Compose**: Discovers implicit bridge hostnames (`sovereign_db`)
- **Kubernetes**: Resolves internal namespace cluster DNS (`postgres.default.svc`)
- **Developer Machine**: Gracefully falls back to `localhost` dynamically.

---

## 🚦 Deployment Options

### A. Orchestrated Fleet (K3s/Kubernetes)
Standard high-availability delivery leverages standard manifests inside `/k8s/`. 
Command: `kubectl apply -f ./k8s/`

### B. Containerized Stack (Docker Compose)
Standard local development and evaluation setup.
Command: `docker compose up -d`
