# 🔍 GameSpy Player Search Server (GPSP) Protocol

The **GameSpy Player Search (GPSP)** server is a supporting partner to the profile subsystem. It manages short-lived, stateless TCP transactions focused entirely on searching for player profiles, validating unique nicknames during account creation, and querying public buddy data.

---

## 📋 Service Blueprint
-   **Protocol:** Stateless TCP (Connect -> Query -> Response -> Close)
-   **Port Binding:** `29901`
-   **Format:** Backslash-delimited ASCII commands (`\key\value\`)

---

## 🧬 Key Queries & Workflows

GPSP evaluates commands to find profiles by unique tags, email, or console profile ID.

### 1. Nickname Validation (`\valid\`)
When a user types a new player name, the console sends this query to ensure no duplicates exist.
```text
\valid\1\email\dwc_runner@nintendo.com\nick\dwc_runner\final\
```

### 2. User Searching (`\search\`)
Used to find friends by typing their display name.
```text
\search\1\sesskey\987654321\nick\alice\final\
```

---

## 🔄 Workflow Discovery Sequence

```mermaid
sequenceDiagram
    participant Console as 🎮 Console Player
    participant Search as 🔍 GPSP Server (TCP 29901)
    participant DB as 🗄️ Postgres DB

    Console->>Search: 1. TCP Connect
    Console->>Search: 2. Request Validation (\valid\1\nick\bob\final\)
    Search->>DB: 3. SELECT COUNT(*) FROM profiles WHERE nick = 'bob'
    DB-->>Search: Return Result Count [Count: 0]
    Search-->>Console: 4. Return \valid\1\nick\bob\isvalid\1\final\
    
    Console->>Search: 5. Send Search Query (\search\1\nick\alice\final\)
    Search->>DB: 6. SELECT id, nick FROM profiles WHERE nick LIKE 'alice%'
    DB-->>Search: Return Match Alice [ID: 444]
    Search-->>Console: 7. Return \searchr\1\id\444\nick\alice\final\
    Note over Console,Search: Socket Severed Cleanly
```

---

## 🗄️ Database Queries Handled

Because searching parses human input, GPSP is optimized to prevent SQL query bottlenecks:

| Objective | Query Vector | DB Security |
| :--- | :--- | :--- |
| **Duplicate Nick Check** | Indexed `EXISTS` check. | Prevents race conditions during multi-thread account creation. |
| **Player Searching** | Bounds-limited SQL `LIKE` clause. | Strict 50-result limits to prevent database thread starvation. |
