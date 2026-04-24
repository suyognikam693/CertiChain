# CertiChain

CertiChain is a decentralized academic credential platform that lets universities issue tamper-evident degree records, anchor them on-chain, store the full credential payload on IPFS, and let students or employers verify proofs without relying on a central database.

The repository is split into two main areas:

- `CertiChain/frontend`: the React and Vite web application for universities, students, and verifiers.
- `CertiChain/system`: the core credential stack, including the FastAPI backend, Hardhat smart contract project, and Dockerized IPFS plus local chain infrastructure.

## What The Project Does

- Issues academic credentials as structured verifiable credential payloads.
- Builds Merkle trees for batch issuance so each credential carries a compact proof.
- Stores enriched credential JSON on IPFS.
- Anchors batch roots and credential pointers on Ethereum-compatible chains.
- Supports local development with Docker, Hardhat, and dual Kubo nodes.
- Supports Sepolia deployment by switching backend and blockchain environment values.

## Repository Layout

```text
CertiChain/
├── frontend/          # React client
├── system/
│   ├── backend/       # FastAPI API, batch logic, IPFS + chain integration
│   ├── blockchain/    # Hardhat project and deployment scripts
│   └── docker/        # Docker Compose for IPFS Cluster + Hardhat node
├── README.md
└── requirements.txt
```

## Quick Start

For the full system walkthrough, start with `CertiChain/system/README.md`.

Typical local setup order:

1. Start infrastructure from `CertiChain/system/docker`.
2. Deploy the smart contract from `CertiChain/system/blockchain`.
3. Configure and run the API from `CertiChain/system/backend`.
4. Start the client from `CertiChain/frontend`.

## Documentation Guide

- `CertiChain/system/README.md`: full architecture and startup order.
- `CertiChain/system/backend/README.md`: backend responsibilities, env variables, and API startup.
- `CertiChain/system/blockchain/README.md`: contract workflow, deploy commands, and network notes.
- `CertiChain/system/docker/README.md`: Docker services, ports, and reset commands.
- `CertiChain/frontend/README.md`: frontend setup and environment configuration.

## Development Notes

- Real `.env` files are intentionally ignored. Use the provided `.env.example` files as templates.
- Generated folders such as `node_modules`, `dist`, `artifacts`, `cache`, and Python virtual environments should not be committed.
- The backend contains both the current API entry point in `CertiChain/system/backend/main.py` and an older experimental file in `CertiChain/system/backend/merklemain.py`. The active path documented here uses `main.py`.
