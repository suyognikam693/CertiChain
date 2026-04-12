#!/bin/sh
set -e

CLUSTER_DATA="/data/ipfs-cluster"

echo "=== cluster1 starting ==="

if [ ! -f "$CLUSTER_DATA/identity.json" ]; then
  echo "Initializing cluster1 identity"
  ipfs-cluster-service init --consensus raft
else
  echo "cluster1 identity exists"
fi

echo "Waiting for ipfs1 API"
RETRIES=30
while [ "$RETRIES" -gt 0 ]; do
  if wget -qO- http://ipfs1:5001/api/v0/id >/dev/null 2>&1; then
    echo "ipfs1 ready"
    break
  fi
  RETRIES=$((RETRIES - 1))
  sleep 3
done

echo "Waiting for cluster0 API"
RETRIES=40
while [ "$RETRIES" -gt 0 ]; do
  if wget -qO- http://cluster0:9094/id >/dev/null 2>&1; then
    break
  fi
  RETRIES=$((RETRIES - 1))
  sleep 3
done

if [ "$RETRIES" -eq 0 ]; then
  echo "cluster0 unavailable, starting cluster1 without bootstrap"
  exec ipfs-cluster-service --debug daemon --upgrade
fi

CLUSTER0_INFO=$(wget -qO- http://cluster0:9094/id 2>/dev/null || echo "")
CLUSTER0_PEER_ID=$(echo "$CLUSTER0_INFO" | grep -o '"id":"[^"]*"' | head -1 | sed 's/"id":"//;s/"//')

if [ -z "$CLUSTER0_PEER_ID" ]; then
  echo "cluster0 peer id unavailable, starting without bootstrap"
  exec ipfs-cluster-service --debug daemon --upgrade
fi

BOOTSTRAP_ADDR="/dns4/cluster0/tcp/9096/p2p/$CLUSTER0_PEER_ID"
echo "Bootstrapping from $BOOTSTRAP_ADDR"
exec ipfs-cluster-service --debug daemon --upgrade --bootstrap "$BOOTSTRAP_ADDR"
