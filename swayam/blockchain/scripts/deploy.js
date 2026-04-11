// scripts/deploy.js
// =============================================================================
// Deploys CredentialVerifier and writes contract_abi.json next to main.py.
//
// Usage:
//   npx hardhat run scripts/deploy.js --network localhost
//
// After deploy, copy the printed CONTRACT_ADDRESS into your .env file.
// =============================================================================

const { ethers } = require("hardhat");
const path        = require("path");
const fs          = require("fs");

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying with account:", deployer.address);

  // ethers v5: deployer.getBalance()
  // ethers v6: ethers.provider.getBalance(deployer.address)
  try {
    const balance = await ethers.provider.getBalance(deployer.address);
    console.log("Account balance:", balance.toString());
  } catch (_) {
    // non-fatal — balance display is informational only
  }

  const CredentialVerifier = await ethers.getContractFactory("CredentialVerifier");
  const contract            = await CredentialVerifier.deploy();

  // ethers v5: contract.deployed()
  // ethers v6: contract.waitForDeployment()
  if (typeof contract.waitForDeployment === "function") {
    await contract.waitForDeployment();
  } else {
    await contract.deployed();
  }

  // ethers v5: contract.address
  // ethers v6: contract.target
  const address = contract.target ?? contract.address;

  console.log("\nCredentialVerifier deployed to:", address);
  console.log("\nAdd to your .env:");
  console.log(`CONTRACT_ADDRESS=${address}`);
  console.log(`UNIVERSITY_ADDRESS=${deployer.address}`);

  // Write ABI next to main.py so the backend loads it automatically.
  const artifactPath = path.join(
    __dirname, "..",
    "artifacts", "contracts", "CredentialVerifier.sol", "CredentialVerifier.json"
  );

  if (fs.existsSync(artifactPath)) {
    const artifact   = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
    const outputPath = path.join(__dirname, "..", "contract_abi.json");
    fs.writeFileSync(outputPath, JSON.stringify(artifact, null, 2));
    console.log(`\nABI written to: ${outputPath}`);
  } else {
    console.warn("\nWARNING: Artifact not found at", artifactPath);
    console.warn("Run `npx hardhat compile` first.");
  }

  // Sanity check — call getBatch with a dummy ID
  const result = await contract.getBatch("__sanity__");
  console.log("\nSanity check getBatch('__sanity__').exists:", result.exists);
  console.log("\nDeployment complete.");
}

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });