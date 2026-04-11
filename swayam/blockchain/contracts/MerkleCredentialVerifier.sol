// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

// =============================================================================
// CredentialVerifier.sol
// =============================================================================
//
// CHANGES vs previous version
// ----------------------------
// 1. commitBatch() ipfsCids[] now stores ENRICHED CIDs (credential JSON with
//    embedded Merkle proof).  No schema change — same string[] param — but the
//    semantics changed: callers must pass enriched CIDs, not bare ones.
//
// 2. getStudentCredentials() returns THREE parallel arrays:
//      string[]  batchIds
//      uint256[] leafIndices
//      string[]  ipfsCids       <- enriched CIDs (contain proof in IPFS)
//    This is what the Python backend reads in get_student_pointers_from_blockchain().
//
// 3. verifyCredential() signature is unchanged:
//      verifyCredential(string batchId, bytes32 credentialHash,
//                       bytes32[] proof, uint256 leafIndex)
//    Returns (bool isValid, bool isRevoked, uint256 committedAt).
//
// =============================================================================

contract CredentialVerifier {

    // -------------------------------------------------------------------------
    // STRUCTS
    // -------------------------------------------------------------------------

    struct Batch {
        bytes32  merkleRoot;
        uint256  credentialCount;
        uint256  committedAt;
        bool     isRevoked;
        bool     exists;
    }

    // Per-student pointer to one credential inside a batch.
    struct CredentialPointer {
        string  batchId;
        uint256 leafIndex;
        string  ipfsCid;    // enriched CID — contains embedded Merkle proof
    }

    // -------------------------------------------------------------------------
    // STATE
    // -------------------------------------------------------------------------

    address public university;

    // batchId -> Batch
    mapping(string => Batch) private batches;

    // studentDid -> list of pointers
    mapping(string => CredentialPointer[]) private studentCredentials;

    // credentialHash -> batchId  (for revocation lookup)
    mapping(bytes32 => string) private credentialBatch;

    // credentialHash -> revoked flag
    mapping(bytes32 => bool) private revokedCredentials;

    // -------------------------------------------------------------------------
    // EVENTS
    // -------------------------------------------------------------------------

    event BatchCommitted(
        string  indexed batchId,
        bytes32         merkleRoot,
        uint256         credentialCount,
        uint256         committedAt
    );

    event CredentialRevoked(
        bytes32 indexed credentialHash,
        string  indexed batchId,
        uint256         revokedAt
    );

    // -------------------------------------------------------------------------
    // MODIFIERS
    // -------------------------------------------------------------------------

    modifier onlyUniversity() {
        require(msg.sender == university, "Only university can call this");
        _;
    }

    // -------------------------------------------------------------------------
    // CONSTRUCTOR
    // -------------------------------------------------------------------------

    constructor() {
        university = msg.sender;
    }

    // -------------------------------------------------------------------------
    // WRITE: commitBatch
    // -------------------------------------------------------------------------

    /**
     * @notice Commits a batch of credentials to the blockchain.
     *
     * @param batchId          Unique identifier for this batch (e.g. "SPIT-2027-CSE")
     * @param merkleRoot       Keccak256 Merkle root of all credential leaf hashes
     * @param credentialCount  Number of credentials in the batch
     * @param studentDids      Parallel array: student DID for each credential
     * @param leafIndices      Parallel array: leaf index in the Merkle tree
     * @param ipfsCids         Parallel array: ENRICHED IPFS CID for each credential
     *                         (the JSON stored at this CID contains the Merkle proof
     *                         embedded under the "merkleProof" key)
     */
    function commitBatch(
        string   calldata   batchId,
        bytes32             merkleRoot,
        uint256             credentialCount,
        string[] calldata   studentDids,
        uint256[] calldata  leafIndices,
        string[] calldata   ipfsCids
    ) external onlyUniversity {
        require(!batches[batchId].exists,          "Batch already committed");
        require(studentDids.length  == credentialCount, "studentDids length mismatch");
        require(leafIndices.length  == credentialCount, "leafIndices length mismatch");
        require(ipfsCids.length     == credentialCount, "ipfsCids length mismatch");
        require(credentialCount > 0,               "Empty batch");

        batches[batchId] = Batch({
            merkleRoot:       merkleRoot,
            credentialCount:  credentialCount,
            committedAt:      block.timestamp,
            isRevoked:        false,
            exists:           true
        });

        for (uint256 i = 0; i < credentialCount; i++) {
            studentCredentials[studentDids[i]].push(CredentialPointer({
                batchId:   batchId,
                leafIndex: leafIndices[i],
                ipfsCid:   ipfsCids[i]
            }));
        }

        emit BatchCommitted(batchId, merkleRoot, credentialCount, block.timestamp);
    }

    // -------------------------------------------------------------------------
    // WRITE: revokeCredential
    // -------------------------------------------------------------------------

    /**
     * @notice Revokes a single credential within a batch.
     *
     * @param credentialHash  SHA-256 leaf hash of the BARE credential
     *                        (without "merkleProof" key — same value used to
     *                        build the Merkle tree leaf)
     * @param batchId         The batch the credential belongs to
     */
    function revokeCredential(
        bytes32         credentialHash,
        string calldata batchId
    ) external onlyUniversity {
        require(batches[batchId].exists,          "Batch not found");
        require(!revokedCredentials[credentialHash], "Already revoked");

        revokedCredentials[credentialHash] = true;
        credentialBatch[credentialHash]    = batchId;

        emit CredentialRevoked(credentialHash, batchId, block.timestamp);
    }

    // -------------------------------------------------------------------------
    // READ: verifyCredential
    // -------------------------------------------------------------------------

    /**
     * @notice Verifies a credential using its Merkle proof.
     *
     * @param batchId         The batch the credential belongs to
     * @param credentialHash  SHA-256 leaf hash of the BARE credential
     * @param proof           Merkle proof (sibling hashes from leaf to root)
     * @param leafIndex       Position of this credential in the batch
     *
     * @return isValid      True if the proof is valid and the batch exists
     * @return isRevoked    True if the credential has been revoked
     * @return committedAt  Unix timestamp when the batch was committed
     */
    function verifyCredential(
        string   calldata  batchId,
        bytes32            credentialHash,
        bytes32[] calldata proof,
        uint256            leafIndex
    ) external view returns (bool isValid, bool isRevoked, uint256 committedAt) {
        Batch storage batch = batches[batchId];

        if (!batch.exists) {
            return (false, false, 0);
        }

        isRevoked    = revokedCredentials[credentialHash];
        committedAt  = batch.committedAt;

        // Verify Merkle proof
        bytes32 computedHash = credentialHash;
        uint256 index        = leafIndex;

        for (uint256 i = 0; i < proof.length; i++) {
            bytes32 sibling = proof[i];
            if (index % 2 == 0) {
                computedHash = keccak256(abi.encodePacked(computedHash, sibling));
            } else {
                computedHash = keccak256(abi.encodePacked(sibling, computedHash));
            }
            index /= 2;
        }

        isValid = (computedHash == batch.merkleRoot);
    }

    // -------------------------------------------------------------------------
    // READ: getBatch
    // -------------------------------------------------------------------------

    /**
     * @notice Returns metadata for a committed batch.
     *
     * @return merkleRoot       bytes32 Merkle root
     * @return credentialCount  Number of credentials
     * @return committedAt      Unix timestamp
     * @return isRevoked        Whether the entire batch is revoked
     * @return exists           Whether this batch ID exists
     */
    function getBatch(string calldata batchId)
        external view
        returns (
            bytes32 merkleRoot,
            uint256 credentialCount,
            uint256 committedAt,
            bool    isRevoked,
            bool    exists
        )
    {
        Batch storage b = batches[batchId];
        return (b.merkleRoot, b.credentialCount, b.committedAt, b.isRevoked, b.exists);
    }

    // -------------------------------------------------------------------------
    // READ: getStudentCredentials
    // -------------------------------------------------------------------------

    /**
     * @notice Returns all credential pointers for a student.
     *
     * The Python backend reads this in get_student_pointers_from_blockchain()
     * and expects exactly three parallel arrays in this order:
     *   [0] string[]  batchIds
     *   [1] uint256[] leafIndices
     *   [2] string[]  ipfsCids    <- ENRICHED CIDs (contain embedded Merkle proofs)
     *
     * @param studentDid  The student's DID string
     */
    function getStudentCredentials(string calldata studentDid)
        external view
        returns (
            string[]  memory batchIds,
            uint256[] memory leafIndices,
            string[]  memory ipfsCids
        )
    {
        CredentialPointer[] storage pointers = studentCredentials[studentDid];
        uint256 n = pointers.length;

        batchIds     = new string[](n);
        leafIndices  = new uint256[](n);
        ipfsCids     = new string[](n);

        for (uint256 i = 0; i < n; i++) {
            batchIds[i]    = pointers[i].batchId;
            leafIndices[i] = pointers[i].leafIndex;
            ipfsCids[i]    = pointers[i].ipfsCid;
        }
    }

    // -------------------------------------------------------------------------
    // READ: isCredentialRevoked  (convenience helper)
    // -------------------------------------------------------------------------

    function isCredentialRevoked(bytes32 credentialHash)
        external view returns (bool)
    {
        return revokedCredentials[credentialHash];
    }
}
