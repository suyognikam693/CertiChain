#!/bin/sh
set -e

CLUSTER_DATA="/data/ipfs-cluster"

echo "=== cluster0 starting ==="

if [ ! -f "$CLUSTER_DATA/identity.json" ]; then
  echo "Initializing cluster0 identity"
  ipfs-cluster-service init --consensus raft
else
  echo "cluster0 identity exists"
fi

echo "Waiting for ipfs0 API"
RETRIES=30
while [ "$RETRIES" -gt 0 ]; do
  if wget -qO- http://ipfs0:5001/api/v0/id >/dev/null 2>&1; then
    echo "ipfs0 ready"
    break
  fi
  RETRIES=$((RETRIES - 1))
  sleep 3
done

echo "Starting cluster0 daemon"
exec ipfs-cluster-service --debug daemon --upgrade
