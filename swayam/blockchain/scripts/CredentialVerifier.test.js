// test/CredentialVerifier.test.js
// =============================================================================
// CONTRACT TESTS
// =============================================================================
// Run: npx hardhat test
// Run with gas: REPORT_GAS=true npx hardhat test
// =============================================================================

const { expect } = require("chai");
const { ethers } = require("hardhat");
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");

describe("CredentialVerifier", function () {

  // ---------------------------------------------------------------------------
  // FIXTURE: Deploy a fresh contract before each test
  // ---------------------------------------------------------------------------
  // loadFixture() is Hardhat's way of resetting state between tests.
  // It snapshots the blockchain after the fixture runs and restores
  // it at the start of each test — much faster than redeploying each time.
  async function deployContractFixture() {
    const [university, student, employer, attacker] = await ethers.getSigners();
    // getSigners() returns Hardhat's test accounts (pre-funded with 10,000 ETH each)

    const CredentialVerifier = await ethers.getContractFactory("CredentialVerifier");
    const contract = await CredentialVerifier.deploy(university.address);
    await contract.waitForDeployment();

    // Sample credential data (matches what FastAPI generates)
    const credentialData = {
      studentDid: "did:ethr:0xStudentAddress123",
      credentialHash: ethers.keccak256(ethers.toUtf8Bytes("test-credential-json")),
      // Note: In production this is SHA-256, but keccak256 works for testing
      ipfsCid: "QmTestCIDabcdef123456",
    };

    return { contract, university, student, employer, attacker, credentialData };
  }

  // ---------------------------------------------------------------------------
  // DEPLOYMENT TESTS
  // ---------------------------------------------------------------------------
  describe("Deployment", function () {
    it("Should set the university address correctly", async function () {
      const { contract, university } = await loadFixture(deployContractFixture);
      expect(await contract.universityAddress()).to.equal(university.address);
    });

    it("Should start with zero credentials", async function () {
      const { contract } = await loadFixture(deployContractFixture);
      expect(await contract.totalCredentials()).to.equal(0);
    });

    it("Should reject zero address as university", async function () {
      const CredentialVerifier = await ethers.getContractFactory("CredentialVerifier");
      await expect(
        CredentialVerifier.deploy(ethers.ZeroAddress)
      ).to.be.revertedWith("University address cannot be zero");
    });
  });

  // ---------------------------------------------------------------------------
  // ISSUE CREDENTIAL TESTS
  // ---------------------------------------------------------------------------
  describe("issueCredential", function () {
    it("Should issue a credential successfully", async function () {
      const { contract, university, credentialData } = await loadFixture(deployContractFixture);

      await expect(
        contract.connect(university).issueCredential(
          credentialData.studentDid,
          credentialData.credentialHash,
          credentialData.ipfsCid
        )
      ).to.emit(contract, "CredentialIssued")
        .withArgs(
          credentialData.credentialHash,
          credentialData.studentDid,
          university.address,
          credentialData.ipfsCid,
          // block.timestamp — we don't check exact value
          await ethers.provider.getBlock("latest").then(b => b.timestamp + 1)
        );
        // Note: The timestamp assertion is approximate due to block timing.
    });

    it("Should increment totalCredentials", async function () {
      const { contract, university, credentialData } = await loadFixture(deployContractFixture);

      await contract.connect(university).issueCredential(
        credentialData.studentDid,
        credentialData.credentialHash,
        credentialData.ipfsCid
      );

      expect(await contract.totalCredentials()).to.equal(1);
    });

    it("Should reject duplicate credentials", async function () {
      const { contract, university, credentialData } = await loadFixture(deployContractFixture);

      // Issue once
      await contract.connect(university).issueCredential(
        credentialData.studentDid,
        credentialData.credentialHash,
        credentialData.ipfsCid
      );

      // Try to issue the same hash again — should fail
      await expect(
        contract.connect(university).issueCredential(
          credentialData.studentDid,
          credentialData.credentialHash,
          credentialData.ipfsCid
        )
      ).to.be.revertedWith("Credential already issued");
    });

    it("Should reject issuance from non-university address", async function () {
      const { contract, attacker, credentialData } = await loadFixture(deployContractFixture);

      await expect(
        contract.connect(attacker).issueCredential(
          credentialData.studentDid,
          credentialData.credentialHash,
          credentialData.ipfsCid
        )
      ).to.be.revertedWith("Only the university can perform this action");
    });

    it("Should reject empty student DID", async function () {
      const { contract, university, credentialData } = await loadFixture(deployContractFixture);

      await expect(
        contract.connect(university).issueCredential(
          "",  // empty DID
          credentialData.credentialHash,
          credentialData.ipfsCid
        )
      ).to.be.revertedWith("Student DID cannot be empty");
    });
  });

  // ---------------------------------------------------------------------------
  // VERIFY CREDENTIAL TESTS
  // ---------------------------------------------------------------------------
  describe("verifyCredential", function () {
    it("Should verify a valid credential", async function () {
      const { contract, university, credentialData } = await loadFixture(deployContractFixture);

      await contract.connect(university).issueCredential(
        credentialData.studentDid,
        credentialData.credentialHash,
        credentialData.ipfsCid
      );

      const [isValid, isRevoked, ipfsCid] = await contract.verifyCredential(
        credentialData.credentialHash
      );

      expect(isValid).to.be.true;
      expect(isRevoked).to.be.false;
      expect(ipfsCid).to.equal(credentialData.ipfsCid);
    });

    it("Should return invalid for non-existent credential", async function () {
      const { contract } = await loadFixture(deployContractFixture);
      const fakeHash = ethers.keccak256(ethers.toUtf8Bytes("fake"));

      const [isValid, isRevoked] = await contract.verifyCredential(fakeHash);

      expect(isValid).to.be.false;
      expect(isRevoked).to.be.false;
    });

    it("Should return invalid after revocation", async function () {
      const { contract, university, credentialData } = await loadFixture(deployContractFixture);

      await contract.connect(university).issueCredential(
        credentialData.studentDid,
        credentialData.credentialHash,
        credentialData.ipfsCid
      );

      await contract.connect(university).revokeCredential(credentialData.credentialHash);

      const [isValid, isRevoked] = await contract.verifyCredential(credentialData.credentialHash);

      expect(isValid).to.be.false;  // Invalid because revoked
      expect(isRevoked).to.be.true;
    });
  });

  // ---------------------------------------------------------------------------
  // REVOKE CREDENTIAL TESTS
  // ---------------------------------------------------------------------------
  describe("revokeCredential", function () {
    it("Should revoke a credential successfully", async function () {
      const { contract, university, credentialData } = await loadFixture(deployContractFixture);

      await contract.connect(university).issueCredential(
        credentialData.studentDid,
        credentialData.credentialHash,
        credentialData.ipfsCid
      );

      await expect(
        contract.connect(university).revokeCredential(credentialData.credentialHash)
      ).to.emit(contract, "CredentialRevoked")
        .withArgs(credentialData.credentialHash, university.address, await ethers.provider.getBlock("latest").then(b => b.timestamp + 1));
    });

    it("Should reject revocation by non-university", async function () {
      const { contract, university, attacker, credentialData } = await loadFixture(deployContractFixture);

      await contract.connect(university).issueCredential(
        credentialData.studentDid,
        credentialData.credentialHash,
        credentialData.ipfsCid
      );

      await expect(
        contract.connect(attacker).revokeCredential(credentialData.credentialHash)
      ).to.be.revertedWith("Only the university can perform this action");
    });

    it("Should reject revoking an already-revoked credential", async function () {
      const { contract, university, credentialData } = await loadFixture(deployContractFixture);

      await contract.connect(university).issueCredential(
        credentialData.studentDid,
        credentialData.credentialHash,
        credentialData.ipfsCid
      );

      await contract.connect(university).revokeCredential(credentialData.credentialHash);

      await expect(
        contract.connect(university).revokeCredential(credentialData.credentialHash)
      ).to.be.revertedWith("Credential already revoked");
    });
  });

  // ---------------------------------------------------------------------------
  // STUDENT CREDENTIALS INDEX TESTS
  // ---------------------------------------------------------------------------
  describe("getStudentCredentials", function () {
    it("Should return all hashes for a student", async function () {
      const { contract, university, credentialData } = await loadFixture(deployContractFixture);

      const hash2 = ethers.keccak256(ethers.toUtf8Bytes("second-credential"));

      await contract.connect(university).issueCredential(
        credentialData.studentDid,
        credentialData.credentialHash,
        credentialData.ipfsCid
      );

      await contract.connect(university).issueCredential(
        credentialData.studentDid,
        hash2,
        "QmSecondCID"
      );

      const hashes = await contract.getStudentCredentials(credentialData.studentDid);

      expect(hashes.length).to.equal(2);
      expect(hashes[0]).to.equal(credentialData.credentialHash);
      expect(hashes[1]).to.equal(hash2);
    });

    it("Should return empty array for unknown student", async function () {
      const { contract } = await loadFixture(deployContractFixture);

      const hashes = await contract.getStudentCredentials("did:ethr:0xUnknown");
      expect(hashes.length).to.equal(0);
    });
  });
});
