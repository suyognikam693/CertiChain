#!/bin/sh
# ipfs1-config/001-configure.sh
# =============================================================================
# IPFS NODE 1 INITIALIZATION SCRIPT
# =============================================================================
#
# Identical to ipfs0-config/001-configure.sh — both nodes are equals in the
# cluster. There is no "primary" vs "replica" distinction at the Kubo level.
# IPFS Cluster manages which CIDs are pinned where.
# =============================================================================

set -e

echo "=== Configuring IPFS Node 1 (for IPFS Cluster) ==="

until ipfs id > /dev/null 2>&1; do
  echo "Waiting for IPFS daemon..."
  sleep 1
done

echo "IPFS daemon ready. Applying configuration..."

ipfs config --json API.HTTPHeaders.Access-Control-Allow-Origin '["http://localhost:8000", "http://localhost:3000", "*"]'
ipfs config --json API.HTTPHeaders.Access-Control-Allow-Methods '["GET", "POST", "PUT", "DELETE"]'
ipfs config --json API.HTTPHeaders.Access-Control-Allow-Headers '["Authorization", "Content-Type"]'

ipfs config --json Gateway.HTTPHeaders.Access-Control-Allow-Origin '["*"]'
ipfs config --json Gateway.HTTPHeaders.Access-Control-Allow-Methods '["GET"]'

ipfs config Addresses.API /ip4/0.0.0.0/tcp/5001
ipfs config Addresses.Gateway /ip4/0.0.0.0/tcp/8080

ipfs config --json Addresses.Swarm '[
  "/ip4/0.0.0.0/tcp/4001",
  "/ip4/0.0.0.0/udp/4001/quic-v1",
  "/ip6/::/tcp/4001",
  "/ip6/::/udp/4001/quic-v1"
]'

ipfs config --json Datastore.GCPeriod '"0s"'
ipfs config Routing.Type dhtclient
ipfs config --json Pubsub.Enabled true

ipfs config --json Swarm.ConnMgr '{
  "Type": "basic",
  "LowWater": 50,
  "HighWater": 100,
  "GracePeriod": "30s"
}'

echo "=== IPFS Node 1 configured successfully ==="
echo "API:     http://0.0.0.0:5001"
echo "Gateway: http://0.0.0.0:8080"
echo "Cluster peer (cluster1) will connect to this node automatically."