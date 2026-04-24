# Blockchain

This folder contains the Hardhat project for the `CredentialVerifier` smart contract used by CertiChain.

## Responsibilities

- compile Solidity contracts
- run local tests
- start a local development chain
- deploy to local Hardhat or Sepolia
- generate the ABI used by the backend

## Key Files

- `CertiChain/system/blockchain/contracts/MerkleCredentialVerifier.sol`: smart contract source
- `CertiChain/system/blockchain/scripts/deploy.js`: deployment script
- `CertiChain/system/blockchain/scripts/CredentialVerifier.test.js`: tests
- `CertiChain/system/blockchain/hardhat.config.js`: Hardhat network configuration
- `CertiChain/system/blockchain/package.json`: scripts and dependencies
- `CertiChain/system/blockchain/.env.example`: network environment template

## Setup

```powershell
cd CertiChain/system/blockchain
npm install
Copy-Item .env.example .env
```

## Available Scripts

```powershell
npm run compile
npm run test
npm run node
npm run deploy:local
npm run deploy:sepolia
npm run clean
```

## Local Development

If you are using the Dockerized local chain, start the services from `CertiChain/system/docker` first and then deploy:

```powershell
npm run deploy:local
```

The deploy script prints:

- `CONTRACT_ADDRESS`
- `UNIVERSITY_ADDRESS`

Copy those values into `CertiChain/system/backend/.env`.

## Sepolia Deployment

Add real values to `.env`:

- `SEPOLIA_RPC_URL`
- `UNIVERSITY_PRIVATE_KEY`
- `ETHERSCAN_API_KEY`

Then run:

```powershell
npm run deploy:sepolia
```

After deployment:

1. copy the deployed contract address into the backend `.env`
2. restart the backend so it reloads the new contract target

## Notes

- `node_modules`, `artifacts`, and `cache` are generated and should stay ignored.
- The backend expects the contract ABI produced by this project.
