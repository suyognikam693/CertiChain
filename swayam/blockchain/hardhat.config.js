require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();
// ADD THIS LINE TEMPORARILY:
console.log("My RPC URL is:", process.env.SEPOLIA_RPC_URL);
/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },

  networks: {
    // Local development (In-memory)
    hardhat: {
      chainId: 31337,
    },
    // Persistent local node (npx hardhat node)
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 31337,
    },
    // --- ADD SEPOLIA HERE ---
  sepolia: {
      url: process.env.SEPOLIA_RPC_URL || "",
      // CHANGE THIS LINE to match your .env variable
      accounts: process.env.UNIVERSITY_PRIVATE_KEY ? [process.env.UNIVERSITY_PRIVATE_KEY] : [],
      chainId: 11155111,
    },
  },

  // Add Etherscan verification so people can see your contract code
  etherscan: {
    apiKey: process.env.ETHERSCAN_API_KEY,
  },

  gasReporter: {
    enabled: process.env.REPORT_GAS !== undefined,
    currency: "USD",
  },

  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
  },
};