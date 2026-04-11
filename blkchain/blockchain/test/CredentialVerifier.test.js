// test/CredentialVerifier.test.js — Hardhat 3 + Mocha + Ethers (ESM)
import { expect } from "chai";
import { network } from "hardhat";

const { ethers, networkHelpers } = await network.connect();

const CREDENTIAL_VERIFIER_FQN = "contracts/CredentialVerifier.sol:CredentialVerifier";

async function deployContractFixture() {
  const [university, student, employer, attacker] = await ethers.getSigners();

  const CredentialVerifier = await ethers.getContractFactory(CREDENTIAL_VERIFIER_FQN);
  const contract = await CredentialVerifier.deploy(university.address);
  await contract.waitForDeployment();

  const credentialData = {
    studentDid: "did:ethr:0xStudentAddress123",
    credentialHash: ethers.keccak256(ethers.toUtf8Bytes("test-credential-json")),
    ipfsCid: "QmTestCIDabcdef123456",
  };

  return { contract, university, student, employer, attacker, credentialData };
}

describe("CredentialVerifier", function () {
  describe("Deployment", function () {
    it("Should set the university address correctly", async function () {
      const { contract, university } = await networkHelpers.loadFixture(deployContractFixture);
      expect(await contract.universityAddress()).to.equal(university.address);
    });

    it("Should start with zero credentials", async function () {
      const { contract } = await networkHelpers.loadFixture(deployContractFixture);
      expect(await contract.totalCredentials()).to.equal(0);
    });

    it("Should reject zero address as university", async function () {
      const CredentialVerifier = await ethers.getContractFactory(CREDENTIAL_VERIFIER_FQN);
      await expect(CredentialVerifier.deploy(ethers.ZeroAddress)).to.be.revertedWith(
        "University address cannot be zero",
      );
    });
  });

  describe("issueCredential", function () {
    it("Should issue a credential successfully", async function () {
      const { contract, university, credentialData } = await networkHelpers.loadFixture(
        deployContractFixture,
      );

      await expect(
        contract.connect(university).issueCredential(
          credentialData.studentDid,
          credentialData.credentialHash,
          credentialData.ipfsCid,
        ),
      )
        .to.emit(contract, "CredentialIssued")
        .withArgs(
          credentialData.credentialHash,
          credentialData.studentDid,
          university.address,
          credentialData.ipfsCid,
          (await ethers.provider.getBlock("latest")).timestamp + 1,
        );
    });

    it("Should increment totalCredentials", async function () {
      const { contract, university, credentialData } = await networkHelpers.loadFixture(
        deployContractFixture,
      );

      await contract.connect(university).issueCredential(
        credentialData.studentDid,
        credentialData.credentialHash,
        credentialData.ipfsCid,
      );

      expect(await contract.totalCredentials()).to.equal(1);
    });

    it("Should reject duplicate credentials", async function () {
      const { contract, university, credentialData } = await networkHelpers.loadFixture(
        deployContractFixture,
      );

      await contract.connect(university).issueCredential(
        credentialData.studentDid,
        credentialData.credentialHash,
        credentialData.ipfsCid,
      );

      await expect(
        contract.connect(university).issueCredential(
          credentialData.studentDid,
          credentialData.credentialHash,
          credentialData.ipfsCid,
        ),
      ).to.be.revertedWith("Credential already issued");
    });

    it("Should reject issuance from non-university address", async function () {
      const { contract, attacker, credentialData } = await networkHelpers.loadFixture(
        deployContractFixture,
      );

      await expect(
        contract.connect(attacker).issueCredential(
          credentialData.studentDid,
          credentialData.credentialHash,
          credentialData.ipfsCid,
        ),
      ).to.be.revertedWith("Only the university can perform this action");
    });

    it("Should reject empty student DID", async function () {
      const { contract, university, credentialData } = await networkHelpers.loadFixture(
        deployContractFixture,
      );

      await expect(
        contract.connect(university).issueCredential("", credentialData.credentialHash, credentialData.ipfsCid),
      ).to.be.revertedWith("Student DID cannot be empty");
    });
  });

  describe("verifyCredential", function () {
    it("Should verify a valid credential", async function () {
      const { contract, university, credentialData } = await networkHelpers.loadFixture(
        deployContractFixture,
      );

      await contract.connect(university).issueCredential(
        credentialData.studentDid,
        credentialData.credentialHash,
        credentialData.ipfsCid,
      );

      const [isValid, isRevoked, ipfsCid] = await contract.verifyCredential(credentialData.credentialHash);

      expect(isValid).to.be.true;
      expect(isRevoked).to.be.false;
      expect(ipfsCid).to.equal(credentialData.ipfsCid);
    });

    it("Should return invalid for non-existent credential", async function () {
      const { contract } = await networkHelpers.loadFixture(deployContractFixture);
      const fakeHash = ethers.keccak256(ethers.toUtf8Bytes("fake"));

      const [isValid, isRevoked] = await contract.verifyCredential(fakeHash);

      expect(isValid).to.be.false;
      expect(isRevoked).to.be.false;
    });

    it("Should return invalid after revocation", async function () {
      const { contract, university, credentialData } = await networkHelpers.loadFixture(
        deployContractFixture,
      );

      await contract.connect(university).issueCredential(
        credentialData.studentDid,
        credentialData.credentialHash,
        credentialData.ipfsCid,
      );

      await contract.connect(university).revokeCredential(credentialData.credentialHash);

      const [isValid, isRevoked] = await contract.verifyCredential(credentialData.credentialHash);

      expect(isValid).to.be.false;
      expect(isRevoked).to.be.true;
    });
  });

  describe("revokeCredential", function () {
    it("Should revoke a credential successfully", async function () {
      const { contract, university, credentialData } = await networkHelpers.loadFixture(
        deployContractFixture,
      );

      await contract.connect(university).issueCredential(
        credentialData.studentDid,
        credentialData.credentialHash,
        credentialData.ipfsCid,
      );

      await expect(contract.connect(university).revokeCredential(credentialData.credentialHash))
        .to.emit(contract, "CredentialRevoked")
        .withArgs(
          credentialData.credentialHash,
          university.address,
          (await ethers.provider.getBlock("latest")).timestamp + 1,
        );
    });

    it("Should reject revocation by non-university", async function () {
      const { contract, university, attacker, credentialData } = await networkHelpers.loadFixture(
        deployContractFixture,
      );

      await contract.connect(university).issueCredential(
        credentialData.studentDid,
        credentialData.credentialHash,
        credentialData.ipfsCid,
      );

      await expect(contract.connect(attacker).revokeCredential(credentialData.credentialHash)).to.be.revertedWith(
        "Only the university can perform this action",
      );
    });

    it("Should reject revoking an already-revoked credential", async function () {
      const { contract, university, credentialData } = await networkHelpers.loadFixture(
        deployContractFixture,
      );

      await contract.connect(university).issueCredential(
        credentialData.studentDid,
        credentialData.credentialHash,
        credentialData.ipfsCid,
      );

      await contract.connect(university).revokeCredential(credentialData.credentialHash);

      await expect(contract.connect(university).revokeCredential(credentialData.credentialHash)).to.be.revertedWith(
        "Credential already revoked",
      );
    });
  });

  describe("getStudentCredentials", function () {
    it("Should return all hashes for a student", async function () {
      const { contract, university, credentialData } = await networkHelpers.loadFixture(
        deployContractFixture,
      );

      const hash2 = ethers.keccak256(ethers.toUtf8Bytes("second-credential"));

      await contract.connect(university).issueCredential(
        credentialData.studentDid,
        credentialData.credentialHash,
        credentialData.ipfsCid,
      );

      await contract.connect(university).issueCredential(credentialData.studentDid, hash2, "QmSecondCID");

      const hashes = await contract.getStudentCredentials(credentialData.studentDid);

      expect(hashes.length).to.equal(2);
      expect(hashes[0]).to.equal(credentialData.credentialHash);
      expect(hashes[1]).to.equal(hash2);
    });

    it("Should return empty array for unknown student", async function () {
      const { contract } = await networkHelpers.loadFixture(deployContractFixture);

      const hashes = await contract.getStudentCredentials("did:ethr:0xUnknown");
      expect(hashes.length).to.equal(0);
    });
  });
});
