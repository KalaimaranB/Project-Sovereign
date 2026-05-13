#!/usr/bin/env bash
# ============================================================
# Project Sovereign — Pi Update Script
# Run this on your Raspberry Pi to apply code changes:
#   chmod +x update.sh && ./update.sh
# ============================================================

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

echo "=== Project Sovereign Updater ==="
echo "Working directory: $REPO_DIR"
echo ""

# ---- 1. Pull latest code ----
echo "[1/6] Pulling latest changes from git..."
# Stash any local changes (like file permission changes) so the pull doesn't fail
git stash
git fetch --all
git pull --rebase
git stash pop || true

# ---- 2. Rebuild containers that changed ----
echo ""
echo "[2/5] Rebuilding changed containers..."
docker compose build --parallel

# ---- 3. Apply rolling restart (zero-downtime for databases) ----
echo ""
echo "[3/5] Restarting services with zero downtime for DB/Redis..."

# Never restart postgres or redis during an update — data safety first
SERVICES=(
  sovereign_nas
  sovereign_qr
  sovereign_profile
  sovereign_natneg
  sovereign_browser
  sovereign_player_search
  sovereign_gamestats
  sovereign_dls1
  sovereign_storage
  sovereign_register
  sovereign_admin
  sovereign_internal_stats
  sovereign_stats_http
  sovereign_patcher
  sovereign_dashboard
  sovereign_dns
  sovereign_tcpdump
)

for svc in "${SERVICES[@]}"; do
  echo "  → Restarting $svc..."
  docker compose restart "$svc" 2>/dev/null || \
    echo "    (skipping $svc — not found in compose file)"
done

# ---- 4. Cleanup old Docker images ----
echo ""
echo "[4/6] Cleaning up old Docker artifacts..."
docker image prune -f

# ---- 5. Verify all containers are up ----
echo ""
echo "[5/6] Verifying container health..."
sleep 3
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

# ---- 6. Quick connectivity check ----
echo ""
echo "[6/6] Connectivity checks..."

NAS_URL="http://localhost:9000/"
STATS_URL="http://localhost:9001/json"
DASH_URL="http://localhost:5173/"

for url in "$NAS_URL" "$STATS_URL" "$DASH_URL"; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "ERR")
  if [ "$STATUS" = "200" ]; then
    echo "  ✓ $url → $STATUS OK"
  else
    echo "  ✗ $url → $STATUS (may need more time to boot)"
  fi
done

echo ""
echo "=== Update complete! ==="
echo ""
echo "Dashboard:  http://$(hostname -I | awk '{print $1}'):5173"
echo "Admin:      http://$(hostname -I | awk '{print $1}'):9009"
echo "Stats JSON: http://$(hostname -I | awk '{print $1}'):9001/json"
echo ""
echo "If devices still can't connect, verify DNS redirects:"
echo "  naswii.nintendowifi.net  →  $(hostname -I | awk '{print $1}')"
echo "  conntest.nintendowifi.net →  $(hostname -I | awk '{print $1}')"