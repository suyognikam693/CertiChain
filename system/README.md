# System Overview

This folder contains the complete credential issuance stack used by CertiChain: the API layer, the smart contract project, and the local infrastructure required to run the system end to end.

## Subsystems

### Backend

`CertiChain/system/backend` contains the FastAPI application that:

- stages credentials into batches
- builds Merkle proofs
- pins enriched JSON payloads to IPFS Cluster
- commits Merkle roots and credential pointers to the smart contract
- serves student, verifier, and health endpoints

### Blockchain

`CertiChain/system/blockchain` contains the Hardhat project that:

- compiles the `CredentialVerifier` smart contract
- runs tests against a local Hardhat chain
- deploys to `localhost` or `sepolia`
- emits the contract address and ABI used by the backend

### Docker

`CertiChain/system/docker` contains the local infrastructure layer:

- `ipfs0` and `ipfs1` Kubo nodes
- `cluster0` and `cluster1` IPFS Cluster peers
- `hardhat-node` for local EVM development

## High-Level Flow

```text
Frontend
   |
   v
FastAPI backend
   |-- pin enriched credentials -> IPFS Cluster -> Kubo nodes
   |-- commit batch root + pointers -> Hardhat / Sepolia contract
   |
   v
Students / Verifiers fetch proof-bearing credentials and verify on-chain
```

## Directory Structure

```text
system/
├── README.md
├── backend/
│   ├── main.py
│   ├── merklemain.py
│   ├── zkp_routes.py
│   ├── contract_abi.json
│   ├── requirements.txt
│   └── .env.example
├── blockchain/
│   ├── contracts/
│   ├── scripts/
│   ├── hardhat.config.js
│   ├── package.json
│   └── .env.example
└── docker/
    ├── docker-compose.yml
    ├── cluster0-config/
    ├── cluster1-config/
    ├── ipfs0-config/
    └── ipfs1-config/
```

## Recommended Startup Order

1. Start infrastructure:
   `CertiChain/system/docker/README.md`
2. Install and deploy the contract:
   `CertiChain/system/blockchain/README.md`
3. Copy backend env values and run the API:
   `CertiChain/system/backend/README.md`
4. Point the frontend at the backend and start the UI:
   `CertiChain/frontend/README.md`

## Local Development Checklist

- Docker Desktop running
- Node.js 18+ and npm available
- Python 3.11+ available
- `system/backend/.env` created from `.env.example`
- `system/blockchain/.env` created from `.env.example` when deploying to Sepolia
- contract deployed and backend `CONTRACT_ADDRESS` updated

## Related Documentation

- `CertiChain/system/backend/README.md`
- `CertiChain/system/blockchain/README.md`
- `CertiChain/system/docker/README.md`
