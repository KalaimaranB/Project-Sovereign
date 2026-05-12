# 🚀 Getting Started with Project Sovereign

Welcome to **Project Sovereign**! This guide is designed to take you from a clean machine to running a fully functional, secure, enterprise-grade Nintendo Wi-Fi Connection server in **under 5 minutes**. 

Whether you are hosting a local LAN party or inviting friends across the globe via our built-in VPN, this is the absolute starting line!

---

## 📋 Phase 1: Pre-requisites

Ensure you have the following systems available before beginning:
1.  **The Host Computer:** A Raspberry Pi (4 or 5), standard Linux Server (Ubuntu/Debian), macOS, or Windows running WSL2.
2.  **Docker & Compose:** Install the standard engine from [Docker's Official Setup](https://docs.docker.com/engine/install/).
3.  **DNS Control:** (For hardware consoles) Ability to point domains on your local network (e.g., via Pi-hole, your router settings, or Dnsmasq).

---

## 🐳 Phase 2: Launching the Microservice Mesh

Project Sovereign is fully containerized. To launch the databases, the high-speed C Firewall, the VPN gateway, and the 11 Python microservices, execute a single orchestrator command:

```bash
# 1. Clone the Repository (if you haven't already)
git clone https://github.com/[YOUR_USERNAME]/Project-Sovereign.git
cd Project-Sovereign

# 2. Fire up the entire secure mesh
docker compose up -d --build
```

Verify that all 14 distinct containers are healthy:
```bash
docker compose ps
```
> You should see all states marked as **Up / Running**! 🎉

---

## 🎮 Phase 3: Connecting Your Nintendo Console

To get your physical DS or Wii to recognize your server instead of the official Nintendo servers (which were shut down in 2014), you need to perform a simple **Domain Redirect**.

### The Rule of Redirection
Instruct your local DNS Server (like Pi-hole) to resolve the following domains to the **LAN IP Address** of your host computer:

```text
naswii.nintendowifi.net      -> [YOUR_SERVER_IP]
conntest.nintendowifi.net    -> [YOUR_SERVER_IP]
*.available.gs.nintendowifi.net -> [YOUR_SERVER_IP]
*.master.gs.nintendowifi.net    -> [YOUR_SERVER_IP]
*.ms.nintendowifi.net        -> [YOUR_SERVER_IP]
gpcm.gs.nintendowifi.net     -> [YOUR_SERVER_IP]
gpsp.gs.nintendowifi.net     -> [YOUR_SERVER_IP]
gamestats.gs.nintendowifi.net -> [YOUR_SERVER_IP]
sake.gs.nintendowifi.net     -> [YOUR_SERVER_IP]
```

*For deep-dive setups on specific DNS servers (Pi-hole, Dnsmasq), read the detailed [Operations Manual](file:///Users/kalaimaranbalasothy/GitHub%20Projects/Project%20Sovereign/docs/OPERATIONS.md#section-3-network-topology--console-dns-routing).*

---

## 📡 Phase 4: Inviting Friends (Zero-Trust VPN Gateway)

If your friends are outside your home network, you **do not** need to forward insecure, legacy game ports on your router! Instead, leverage the built-in WireGuard UI.

1.  Open **[http://localhost:51821](http://localhost:51821)** in your web browser.
2.  Enter your dashboard password (configured in `docker-compose.yml`).
3.  Click **+ New Client** and type your friend's name (e.g., `alice_ds`).
4.  **Onboard Instantly:**
    *   📲 Ask Alice to download the official WireGuard app on her phone and **Scan the QR Code** on your screen.
    *   She is now securely connected inside your private Docker network and her DNS is automatically configured!

---

## 🔑 Phase 5: Creating Player Accounts

Legacy Nintendo consoles don't have convenient keyboards. To make registration easy:

1.  Direct your web browser to the registration portal: **[http://localhost:9998](http://localhost:9998)**.
2.  Enter a unique **Nickname**, an **Email**, and a **Password**.
3.  Click **Register**. 

Your new profile is instantly seeded into the PostgreSQL database. Now simply boot up your game, type those exact credentials into the in-game connection menu, and start racing!

---

## 📚 Next Steps

Now that you are up and running, explore the advanced internals of your server:
*   📈 **Monitor Real-Time Data:** Check out the operator panel at **[http://localhost:9009](http://localhost:9009)** to whitelist MAC addresses or ban abusers.
*   🏛️ **Technical Specs:** Deep dive into the packet hex tracings of all 11 servers in the **[Technical Knowledge Base](file:///Users/kalaimaranbalasothy/GitHub%20Projects/Project%20Sovereign/docs/README.md)**.
