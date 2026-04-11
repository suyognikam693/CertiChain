// scripts/deploy.js — Hardhat 3 (ESM, explicit network connection)
import { network } from "hardhat";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function main() {
  const { ethers } = await network.connect();

  console.log("=".repeat(60));
  console.log("Deploying CredentialVerifier contract...");
  console.log("=".repeat(60));

  const [deployer] = await ethers.getSigners();

  console.log(`Deploying with account: ${deployer.address}`);

  const balance = await ethers.provider.getBalance(deployer.address);
  console.log(`Deployer balance: ${ethers.formatEther(balance)} ETH`);

  if (balance === 0n) {
    console.error("ERROR: Deployer account has no ETH. Cannot pay gas fees.");
    console.error("For localhost: run `npx hardhat node` first.");
    console.error("For Sepolia: get ETH from https://sepoliafaucet.com/");
    process.exit(1);
  }

  const CredentialVerifier = await ethers.getContractFactory(
    "contracts/CredentialVerifier.sol:CredentialVerifier",
  );
  const contract = await CredentialVerifier.deploy(deployer.address);
  await contract.waitForDeployment();

  const contractAddress = await contract.getAddress();
  const net = await ethers.provider.getNetwork();
  console.log(`\n✅ Contract deployed at: ${contractAddress}`);
  console.log(`   Chain ID: ${net.chainId}`);
  console.log(`   University address: ${deployer.address}`);

  const artifactPath = path.join(
    __dirname,
    "../artifacts/contracts/CredentialVerifier.sol/CredentialVerifier.json",
  );

  if (fs.existsSync(artifactPath)) {
    const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
    const backendAbiPath = path.join(__dirname, "../../backend/contract_abi.json");
    fs.writeFileSync(backendAbiPath, JSON.stringify(artifact.abi, null, 2));
    console.log(`\n✅ ABI saved to: backend/contract_abi.json`);
  }

  console.log("\n" + "=".repeat(60));
  console.log("Copy these into your backend/.env file:");
  console.log("=".repeat(60));
  console.log(`CONTRACT_ADDRESS=${contractAddress}`);
  console.log(`UNIVERSITY_ADDRESS=${deployer.address}`);
  console.log(`HARDHAT_NODE_URL=http://127.0.0.1:8545`);

  if (net.chainId === 31337n) {
    console.log(`\n# For local dev only (Hardhat test account #0):`);
    console.log(`UNIVERSITY_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80`);
    console.log(`# ⚠️  Never use this key on mainnet — it's publicly known!`);
  }

  console.log("=".repeat(60));
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("Deployment failed:", error);
    process.exit(1);
  });
