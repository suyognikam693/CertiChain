import { network } from "hardhat";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function main() {
  const { ethers } = await network.connect();
  const [deployer] = await ethers.getSigners();
  console.log("Deploying with account:", deployer.address);

  try {
    const balance = await ethers.provider.getBalance(deployer.address);
    console.log("Account balance:", balance.toString());
  } catch (_) {}

  const CredentialVerifier = await ethers.getContractFactory("CredentialVerifier");
  const contract = await CredentialVerifier.deploy();

  if (typeof contract.waitForDeployment === "function") {
    await contract.waitForDeployment();
  } else {
    await contract.deployed();
  }

  const address = contract.target ?? contract.address;

  console.log("\nCredentialVerifier deployed to:", address);
  console.log("\nAdd to your .env:");
  console.log(`CONTRACT_ADDRESS=${address}`);
  console.log(`UNIVERSITY_ADDRESS=${deployer.address}`);

  const artifactPath = path.join(
    __dirname,
    "..",
    "artifacts",
    "contracts",
    "MerkleCredentialVerifier.sol",
    "CredentialVerifier.json"
  );

  if (fs.existsSync(artifactPath)) {
    const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
    const outputPath = path.join(__dirname, "..", "contract_abi.json");
    fs.writeFileSync(outputPath, JSON.stringify(artifact, null, 2));
    console.log(`\nABI written to: ${outputPath}`);
  } else {
    console.warn("\nWARNING: Artifact not found at", artifactPath);
    console.warn("Run npx hardhat compile first.");
  }

  const result = await contract.getBatch("__sanity__");
  console.log("\nSanity check getBatch('__sanity__').exists:", result.exists);
  console.log("\nDeployment complete.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});