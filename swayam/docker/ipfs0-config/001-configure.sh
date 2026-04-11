#!/bin/sh
# ipfs0-config/001-configure.sh
# =============================================================================
# IPFS NODE 0 INITIALIZATION SCRIPT
# =============================================================================
#
# Configures the Kubo (IPFS) daemon for use with IPFS Cluster.
#
# KEY DIFFERENCES FROM THE OLD WRITE-NODE CONFIG:
#   - We do NOT expose the IPFS API publicly — cluster peers handle all pinning.
#   - We do NOT manually peer with another Kubo node — Cluster handles that.
#   - CORS is still set for the Gateway (browser fetches content by CID).
#   - The cluster peer (cluster0) talks to us via Docker network (ipfs0:5001).
# =============================================================================

set -e

echo "=== Configuring IPFS Node 0 (for IPFS Cluster) ==="

until ipfs id > /dev/null 2>&1; do
  echo "Waiting for IPFS daemon..."
  sleep 1
done

echo "IPFS daemon ready. Applying configuration..."

# ---------------------------------------------------------------------------
# 1. API CORS
# ---------------------------------------------------------------------------
# FastAPI (and the cluster peer) call the IPFS API on port 5001.
# The cluster peer talks node-to-node inside Docker — no browser involved —
# so CORS here is only needed if you call the API directly from a browser.
ipfs config --json API.HTTPHeaders.Access-Control-Allow-Origin '["http://localhost:8000", "http://localhost:3000", "*"]'
ipfs config --json API.HTTPHeaders.Access-Control-Allow-Methods '["GET", "POST", "PUT", "DELETE"]'
ipfs config --json API.HTTPHeaders.Access-Control-Allow-Headers '["Authorization", "Content-Type"]'

# ---------------------------------------------------------------------------
# 2. GATEWAY CORS
# ---------------------------------------------------------------------------
# The Gateway (port 8080) serves IPFS content to browsers by CID.
# Browsers need CORS headers to fetch content cross-origin.
ipfs config --json Gateway.HTTPHeaders.Access-Control-Allow-Origin '["*"]'
ipfs config --json Gateway.HTTPHeaders.Access-Control-Allow-Methods '["GET"]'

# ---------------------------------------------------------------------------
# 3. LISTEN ADDRESSES
# ---------------------------------------------------------------------------
# 0.0.0.0 = accept connections from other Docker containers.
ipfs config Addresses.API /ip4/0.0.0.0/tcp/5001
ipfs config Addresses.Gateway /ip4/0.0.0.0/tcp/8080

ipfs config --json Addresses.Swarm '[
  "/ip4/0.0.0.0/tcp/4001",
  "/ip4/0.0.0.0/udp/4001/quic-v1",
  "/ip6/::/tcp/4001",
  "/ip6/::/udp/4001/quic-v1"
]'

# ---------------------------------------------------------------------------
# 4. GARBAGE COLLECTION — DISABLE
# ---------------------------------------------------------------------------
# IPFS Cluster handles all pins. Cluster tells the IPFS node what to pin.
# We disable GC so the IPFS node never removes content that cluster pinned.
# (Pinned content is never GC'd regardless, but belt-and-suspenders.)
ipfs config --json Datastore.GCPeriod '"0s"'

# ---------------------------------------------------------------------------
# 5. ROUTING
# ---------------------------------------------------------------------------
ipfs config Routing.Type dhtclient

# ---------------------------------------------------------------------------
# 6. CONNECTION MANAGER
# ---------------------------------------------------------------------------
# Slightly higher water marks than before because cluster peers also
# maintain connections through us for content routing.
ipfs config --json Swarm.ConnMgr '{
  "Type": "basic",
  "LowWater": 50,
  "HighWater": 100,
  "GracePeriod": "30s"
}'

# ---------------------------------------------------------------------------
# 7. PUBSUB — Required for IPFS Cluster's pubsub-based peer discovery
# ---------------------------------------------------------------------------
# IPFS Cluster can use pubsub to broadcast pin operations to all peers.
# Enabling it on the Kubo node is a prerequisite.
ipfs config --json Pubsub.Enabled true

echo "=== IPFS Node 0 configured successfully ==="
echo "API:     http://0.0.0.0:5001"
echo "Gateway: http://0.0.0.0:8080"
echo "Cluster peer (cluster0) will connect to this node automatically."