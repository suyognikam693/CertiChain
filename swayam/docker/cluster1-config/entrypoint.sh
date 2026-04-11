#!/bin/sh
# cluster1-config/entrypoint.sh
# =============================================================================
# IPFS CLUSTER PEER 1 — ENTRYPOINT SCRIPT
# =============================================================================
#
# Same init pattern as cluster0, PLUS:
#   - Waits for cluster0 to be healthy.
#   - Fetches cluster0's cluster peer ID dynamically.
#   - Passes it as --bootstrap so cluster1 joins the existing Raft cluster.
#
# WHY DYNAMIC PEER ID DISCOVERY?
#   The cluster peer ID is generated on first boot and stored in identity.json.
#   We cannot know it at docker-compose.yml write time.
#   So cluster1 queries cluster0's REST API (/id endpoint) at runtime,
#   extracts the peer ID, and passes it as --bootstrap to the daemon.
#
#   After the first successful join, cluster1 persists the peer list in its
#   own datastore. On subsequent restarts, --bootstrap is ignored if peers
#   are already known — so this dynamic lookup only matters for the first boot.
# =============================================================================

set -e

CLUSTER_DATA="/data/ipfs-cluster"

echo "=== IPFS Cluster Peer 1 starting ==="

# ---------------------------------------------------------------------------
# INITIALISE on first boot
# ---------------------------------------------------------------------------
if [ ! -f "$CLUSTER_DATA/identity.json" ]; then
  echo "First boot: initialising cluster identity..."
  ipfs-cluster-service init --consensus raft
  echo "Cluster identity initialised."
else
  echo "Existing identity found. Skipping init."
fi

# ---------------------------------------------------------------------------
# WAIT for ipfs1 (our local IPFS node)
# ---------------------------------------------------------------------------
echo "Waiting for ipfs1 API..."
RETRIES=30
while [ $RETRIES -gt 0 ]; do
  if wget -qO- http://ipfs1:5001/api/v0/id > /dev/null 2>&1; then
    echo "ipfs1 is ready."
    break
  fi
  echo "  Not yet... ($RETRIES retries left)"
  RETRIES=$((RETRIES - 1))
  sleep 3
done

if [ $RETRIES -eq 0 ]; then
  echo "WARNING: ipfs1 did not become ready in time. Continuing..."
fi

# ---------------------------------------------------------------------------
# WAIT for cluster0 REST API
# ---------------------------------------------------------------------------
echo "Waiting for cluster0 REST API (port 9094)..."
RETRIES=40
while [ $RETRIES -gt 0 ]; do
  if wget -qO- http://cluster0:9094/id > /dev/null 2>&1; then
    echo "cluster0 REST API is reachable."
    break
  fi
  echo "  Not yet... ($RETRIES retries left)"
  RETRIES=$((RETRIES - 1))
  sleep 3
done

if [ $RETRIES -eq 0 ]; then
  echo "WARNING: cluster0 not reachable. Peer 1 will start without bootstrap."
  echo "Starting IPFS Cluster daemon (peer 1, no bootstrap)..."
  exec ipfs-cluster-service --debug daemon --upgrade
fi

# ---------------------------------------------------------------------------
# FETCH cluster0's CLUSTER peer ID
# ---------------------------------------------------------------------------
# The /id endpoint returns JSON like:
# {
#   "id": "12D3KooW...",      ← this is the CLUSTER peer ID (not IPFS peer ID)
#   "addresses": [...],
#   "version": "1.0.8",
#   ...
# }
CLUSTER0_INFO=$(wget -qO- http://cluster0:9094/id 2>/dev/null || echo "")

if [ -z "$CLUSTER0_INFO" ]; then
  echo "WARNING: Could not fetch cluster0 peer info. Starting without bootstrap."
  exec ipfs-cluster-service --debug daemon --upgrade
fi

# Extract peer ID with grep + sed (no jq in the Alpine image).
CLUSTER0_PEER_ID=$(echo "$CLUSTER0_INFO" | grep -o '"id":"[^"]*"' | head -1 | sed 's/"id":"//;s/"//')

if [ -z "$CLUSTER0_PEER_ID" ]; then
  echo "WARNING: Could not parse cluster0 peer ID. Starting without bootstrap."
  exec ipfs-cluster-service --debug daemon --upgrade
fi

echo "cluster0 peer ID: $CLUSTER0_PEER_ID"

# Build the cluster multiaddress for cluster0.
# Format: /dns4/<hostname>/tcp/<cluster-swarm-port>/p2p/<cluster-peer-id>
BOOTSTRAP_ADDR="/dns4/cluster0/tcp/9096/p2p/$CLUSTER0_PEER_ID"
echo "Bootstrap address: $BOOTSTRAP_ADDR"

# ---------------------------------------------------------------------------
# START the cluster daemon WITH bootstrap
# ---------------------------------------------------------------------------
echo "Starting IPFS Cluster daemon (peer 1, bootstrapping from cluster0)..."
exec ipfs-cluster-service \
  --debug \
  daemon \
  --upgrade \
  --bootstrap "$BOOTSTRAP_ADDR"