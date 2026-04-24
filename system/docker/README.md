# Docker Infrastructure

This folder contains the local infrastructure used by CertiChain for development and testing.

## Services

- `ipfs0`: primary Kubo node
- `ipfs1`: secondary Kubo node
- `cluster0`: IPFS Cluster peer managing `ipfs0`
- `cluster1`: IPFS Cluster peer managing `ipfs1`
- `hardhat-node`: local Ethereum-compatible development chain

## Main File

- `CertiChain/system/docker/docker-compose.yml`

## Service Ports

### IPFS

- `ipfs0` API: `5001`
- `ipfs0` gateway: `8080`
- `ipfs0` swarm: `4001`
- `ipfs1` API: `5003`
- `ipfs1` gateway: `8082`
- `ipfs1` swarm: `4003`

### IPFS Cluster

- `cluster0` REST API: `9094`
- `cluster0` libp2p: `9096`
- `cluster1` REST API: `9194`
- `cluster1` libp2p: `9196`

### Blockchain

- `hardhat-node`: `8545`

## Start The Stack

```powershell
cd CertiChain/system/docker
docker compose up -d
docker compose ps
```

To watch logs:

```powershell
docker compose logs -f
```

## Stop The Stack

```powershell
docker compose down
```

## Reset Local State

Use this only when you intentionally want a fresh local environment:

```powershell
docker compose down -v
```

This removes local volumes, including IPFS and cluster state.

## Typical Debug Commands

```powershell
docker logs cluster0 --tail 100
docker logs cluster1 --tail 100
docker exec cluster0 ipfs-cluster-ctl id
docker exec ipfs0 ipfs id
docker exec ipfs1 ipfs id
```

## Notes

- The backend expects `cluster0` to be reachable on `http://localhost:9094`.
- The backend reads content from the Kubo gateways and can fall back to Kubo API endpoints.
- If the contract appears to disappear locally, remember that restarting Hardhat resets chain state and requires redeployment.
