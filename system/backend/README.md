# Backend

This service is the operational core of CertiChain. It coordinates credential staging, Merkle proof generation, IPFS persistence, blockchain commits, and verifier-friendly read APIs.

## Responsibilities

- accept manual or CSV-based credential staging
- batch credentials before commit
- compute Merkle roots and per-leaf proofs
- pin enriched credential payloads to IPFS Cluster
- commit batch metadata and credential pointers to the smart contract
- fetch credential data back from IPFS for student and verifier flows
- expose health and debugging endpoints for local development

## Key Files

- `CertiChain/system/backend/main.py`: primary FastAPI app
- `CertiChain/system/backend/merklemain.py`: older experimental backend variant
- `CertiChain/system/backend/zkp_routes.py`: zero-knowledge proof related routes
- `CertiChain/system/backend/contract_abi.json`: ABI consumed by Web3
- `CertiChain/system/backend/requirements.txt`: Python dependencies
- `CertiChain/system/backend/.env.example`: environment template

## Prerequisites

- Python 3.11+
- Docker services running from `CertiChain/system/docker`
- Contract deployed from `CertiChain/system/blockchain`

## Setup

```powershell
cd CertiChain/system/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill in `.env` with the deployed contract address and the correct network values.

## Important Environment Variables

- `HARDHAT_NODE_URL`: RPC endpoint for local Hardhat or Sepolia
- `CONTRACT_ADDRESS`: deployed `CredentialVerifier` contract address
- `UNIVERSITY_ADDRESS`: wallet that deployed and signs contract writes
- `UNIVERSITY_PRIVATE_KEY`: signer private key
- `CLUSTER_API_URL`: IPFS Cluster REST API
- `CLUSTER_GATEWAY_URLS`: IPFS HTTP gateways used for content retrieval
- `IPFS_API_URLS`: fallback Kubo API endpoints for direct `cat` reads
- `API_KEY`: backend-issued shared token used by protected UI actions
- `FRONTEND_URL`: frontend base URL used in generated links

## Run

```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open:

- API docs: `http://localhost:8000/docs`
- health: `http://localhost:8000/health`

## Typical Local Workflow

1. start Docker services
2. deploy the contract from `system/blockchain`
3. copy contract address and signer values into `.env`
4. start the backend
5. use the frontend to stage, commit, and verify credentials

## Notes

- `main.py` is the documented and recommended entry point.
- Real `.env` files should never be committed.
- If the student page shows empty proof data, check backend logs for IPFS fetch failures first.
