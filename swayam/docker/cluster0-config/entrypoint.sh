#!/bin/sh
# cluster0-config/entrypoint.sh
# =============================================================================
# IPFS CLUSTER PEER 0 — ENTRYPOINT SCRIPT
# =============================================================================
#
# This runs INSTEAD OF the default ipfs-cluster-service entrypoint.
# It handles first-boot initialisation and then starts the daemon.
#
# WHY A CUSTOM ENTRYPOINT?
#   ipfs-cluster-service needs to be "init"ed on first boot to generate:
#     - A cluster peer identity (peer ID + private key)
#     - A default service.json config file
#   On subsequent boots, it skips init and uses the existing identity.
#
# CLUSTER0 IS THE BOOTSTRAP PEER:
#   It starts alone (no CLUSTER_BOOTSTRAP env) and creates the Raft cluster.
#   cluster1's entrypoint fetches cluster0's peer ID and connects to it.
#
# DATA DIRECTORY:
#   /data/ipfs-cluster — mounted as a Docker volume (cluster0-data).
#   Persists the peer identity, Raft log, and pin datastore across restarts.
# =============================================================================

set -e

CLUSTER_DATA="/data/ipfs-cluster"

echo "=== IPFS Cluster Peer 0 starting ==="

# ---------------------------------------------------------------------------
# INITIALISE on first boot (identity + config generation)
# ---------------------------------------------------------------------------
# If the identity file doesn't exist, this is the first boot.
# ipfs-cluster-service init generates:
#   - identity.json  (peer ID + private key)
#   - service.json   (default config, overridable by env vars)
if [ ! -f "$CLUSTER_DATA/identity.json" ]; then
  echo "First boot: initialising cluster identity..."
  ipfs-cluster-service init --consensus raft
  # --consensus raft  → use Raft for pin set agreement (vs crdt for larger clusters)
  # CRDT is eventually consistent; Raft is strongly consistent.
  # For 2 peers, Raft is preferred — CRDT works better with 3+ peers.
  echo "Cluster identity initialised."
else
  echo "Existing identity found. Skipping init."
fi

# ---------------------------------------------------------------------------
# WAIT for the local IPFS node to be ready
# ---------------------------------------------------------------------------
echo "Waiting for ipfs0 API to be available..."
RETRIES=30
while [ $RETRIES -gt 0 ]; do
  if wget -qO- http://ipfs0:5001/api/v0/id > /dev/null 2>&1; then
    echo "ipfs0 is ready."
    break
  fi
  echo "  Not yet... ($RETRIES retries left)"
  RETRIES=$((RETRIES - 1))
  sleep 3
done

if [ $RETRIES -eq 0 ]; then
  echo "ERROR: ipfs0 did not become ready. Cluster may not function correctly."
  # Continue anyway — cluster will retry connecting to IPFS internally.
fi

# ---------------------------------------------------------------------------
# START the cluster daemon
# ---------------------------------------------------------------------------
# Key flags:
#   --debug    → verbose logging (remove in production)
#   daemon     → run in foreground (Docker keeps it alive)
#
# All configuration is driven by environment variables set in docker-compose.yml.
# env vars override service.json values. See:
# https://ipfscluster.io/documentation/reference/configuration/

echo "Starting IPFS Cluster daemon (peer 0)..."
exec ipfs-cluster-service \
  --debug \
  daemon \
  --upgrade
# --upgrade: auto-migrate datastore format on version upgrades (safe to include)