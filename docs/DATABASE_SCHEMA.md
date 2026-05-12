# 🐘 Project Sovereign Database Schema

This document serves as the definitive authoritative reference for the high-availability PostgreSQL backend powering the Project Sovereign network emulation mesh.

## 📑 Table Catalog

### 1. `users` (Primary Account Ledger)
Holds the definitive account records for game clients across all server branches.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `profileid` | `SERIAL` | `PRIMARY KEY` | Unique global player sequence identifier. |
| `uniquenick` | `TEXT` | `UNIQUE`, `NOT NULL` | Canonical display nickname. |
| `userid` | `TEXT` | `NOT NULL` | User identifier often mapping to device hashes. |
| `password` | `TEXT` | | Account security credential. |
| `email` | `TEXT` | | Registered contact verification point. |
| `gsbrcd` | `TEXT` | | Legacy GameSpy brand/client differentiator. |
| `console` | `INT` | | Target platform hardware mapping integer. |

**Key Indices**:
- `users_userid_idx` (B-Tree on `userid`) enabling high-speed device logins.

---

### 2. `gamestat_profile` (Telemetry & Blob Persistence)
Houses complex binary game saves, leaderboard data, and serialized game statistics.

| Column | Type | Description |
|--------|------|-------------|
| `profileid` | `INT` | Foreign reference back to specific player ledger. |
| `dindex` | `TEXT` | The specific save-slot index label (e.g. '0', '1'). |
| `ptype` | `TEXT` | Profile type category (e.g. 'global', 'stats'). |
| `data` | `TEXT` | The actual opaque serialized telemetry payload. |

**Constraints**:
- `UNIQUE(profileid, dindex, ptype)`
- This unlocks high-performance atomic `UPSERT` (ON CONFLICT) logic eliminating race-conditions.

---

### 3. `nas_logins` (Active Ticket Ledger)
Tracks ephemeral authentication handshakes and challenge tickets during login phase.

| Column | Type | Description |
|--------|------|-------------|
| `userid` | `TEXT` | Active device sequence. |
| `authtoken` | `TEXT` | Generated unique validation token. |
| `data` | `TEXT` | JSON-serialized dynamic context (IP, timestamps, challenges). |

---

### 4. `buddies` (Social Graph Ledger)
Manages established peer relations and persistent blocklists.

| Column | Type | Description |
|--------|------|-------------|
| `userProfileId` | `INT` | The source requesting player profile ID. |
| `buddyProfileId` | `INT` | The target relationship player profile ID. |
| `status` | `INT` | Integer encoding (e.g., 1=Request, 2=Accepted). |
| `blocked` | `INT` | Binary block flag (0=No, 1=Blocked). |

---

### 📝 Maintenance / Access Notes
1. **Connection Pooling**: Standard operation utilizes the `asyncpg` lifecycle management pool, configured via global ambient `DATABASE_URL`.
2. **Auto-Generation**: Bootstrapping tables is handled purely by Python startup scripts (`initialize_database()`) which implement explicit `CREATE TABLE IF NOT EXISTS` safety wrappers automatically.
