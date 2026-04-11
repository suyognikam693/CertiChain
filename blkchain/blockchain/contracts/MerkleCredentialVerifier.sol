// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract CredentialVerifier {

    address public immutable universityAddress;

    // =========================================================================
    // NEW: Store batch roots instead of individual hashes
    // =========================================================================
    // batchId → MerkleRoot
    // One root represents potentially thousands of credentials.
    // Storing a bytes32 root costs ~20,000 gas regardless of batch size.
    mapping(string => bytes32) public batchRoots;

    // batchId → metadata
    struct Batch {
        bytes32 merkleRoot;
        uint256 credentialCount;  // how many credentials in this batch
        uint256 committedAt;
        bool    isRevoked;        // can revoke entire batch (e.g., fraud)
        bool    exists;
    }
    mapping(string => Batch) public batches;

    // Individual revocations (specific credential within a batch)
    // credentialHash → revoked
    mapping(bytes32 => bool) public revokedCredentials;

    // studentDid → list of (batchId, leafIndex) so they can find their proof
    struct CredentialPointer {
        string  batchId;
        uint256 leafIndex;   // position in the Merkle tree
        string  ipfsCid;
    }
    mapping(string => CredentialPointer[]) private studentCredentials;

    uint256 public totalBatches;
    uint256 public totalCredentials;

    // =========================================================================
    // EVENTS
    // =========================================================================
    event BatchCommitted(
        string  indexed batchId,
        bytes32 indexed merkleRoot,
        uint256 credentialCount,
        address committedBy,
        uint256 committedAt
    );

    event CredentialRevoked(
        bytes32 indexed credentialHash,
        string  indexed batchId,
        address revokedBy
    );

    event BatchRevoked(
        string  indexed batchId,
        address revokedBy
    );

    // =========================================================================
    // MODIFIER
    // =========================================================================
    modifier onlyUniversity() {
        require(msg.sender == universityAddress, "Only university can do this");
        _;
    }

    constructor(address _universityAddress) {
        require(_universityAddress != address(0), "Zero address not allowed");
        universityAddress = _universityAddress;
    }

    // =========================================================================
    // WRITE: Commit a batch (ONE transaction for N credentials)
    // =========================================================================
    function commitBatch(
        string  calldata batchId,
        bytes32 merkleRoot,
        uint256 credentialCount,
        string[] calldata studentDids,
        uint256[] calldata leafIndices,
        string[] calldata ipfsCids
    ) external onlyUniversity {
        require(!batches[batchId].exists, "Batch already committed");
        require(merkleRoot != bytes32(0), "Root cannot be zero");
        require(credentialCount > 0, "Batch cannot be empty");
        require(
            studentDids.length == leafIndices.length &&
            leafIndices.length == ipfsCids.length,
            "Array lengths must match"
        );

        // Store the batch root — this is what verification is checked against
        batches[batchId] = Batch({
            merkleRoot:      merkleRoot,
            credentialCount: credentialCount,
            committedAt:     block.timestamp,
            isRevoked:       false,
            exists:          true
        });

        // Index each student → their position in this batch
        for (uint256 i = 0; i < studentDids.length; i++) {
            studentCredentials[studentDids[i]].push(CredentialPointer({
                batchId:   batchId,
                leafIndex: leafIndices[i],
                ipfsCid:   ipfsCids[i]
            }));
        }

        totalBatches++;
        totalCredentials += credentialCount;

        emit BatchCommitted(
            batchId,
            merkleRoot,
            credentialCount,
            msg.sender,
            block.timestamp
        );
    }

    // =========================================================================
    // WRITE: Revoke a single credential within a batch
    // =========================================================================
    function revokeCredential(
        bytes32 credentialHash,
        string calldata batchId
    ) external onlyUniversity {
        require(batches[batchId].exists, "Batch does not exist");
        require(!revokedCredentials[credentialHash], "Already revoked");
        revokedCredentials[credentialHash] = true;
        emit CredentialRevoked(credentialHash, batchId, msg.sender);
    }

    // =========================================================================
    // READ: Verify a credential using its Merkle proof
    // =========================================================================
    // The smart contract itself verifies the proof on-chain.
    // This is the authoritative check — no need to trust the backend.
    function verifyCredential(
        string  calldata batchId,
        bytes32 credentialHash,    // hash of the full credential JSON
        bytes32[] calldata proof,  // sibling hashes from leaf to root
        uint256 leafIndex          // position of this leaf in the tree
    ) external view returns (
        bool isValid,
        bool isRevoked,
        uint256 batchCommittedAt
    ) {
        Batch storage batch = batches[batchId];

        if (!batch.exists || batch.isRevoked) {
            return (false, batch.isRevoked, 0);
        }

        // Check individual revocation
        if (revokedCredentials[credentialHash]) {
            return (false, true, batch.committedAt);
        }

        // Reconstruct Merkle root from proof and compare to stored root
        bool proofValid = _verifyMerkleProof(
            proof,
            batch.merkleRoot,
            credentialHash,
            leafIndex
        );

        return (proofValid, false, batch.committedAt);
    }

    // =========================================================================
    // INTERNAL: Merkle proof verification (the core algorithm)
    // =========================================================================
    function _verifyMerkleProof(
        bytes32[] calldata proof,
        bytes32 root,
        bytes32 leaf,
        uint256 index           // leaf position (determines left/right at each level)
    ) internal pure returns (bool) {
        bytes32 computedHash = leaf;

        for (uint256 i = 0; i < proof.length; i++) {
            bytes32 sibling = proof[i];

            if (index % 2 == 0) {
                // Current node is LEFT child → hash(current + sibling)
                computedHash = keccak256(abi.encodePacked(computedHash, sibling));
            } else {
                // Current node is RIGHT child → hash(sibling + current)
                computedHash = keccak256(abi.encodePacked(sibling, computedHash));
            }

            index /= 2;  // Move up one level
            // index/2 gives the parent's index at the next level
        }

        return computedHash == root;
    }

    // =========================================================================
    // READ: Get student's credential pointers
    // =========================================================================
    function getStudentCredentials(string calldata studentDid)
        external view
        returns (
            string[]  memory batchIds,
            uint256[] memory leafIndices,
            string[]  memory ipfsCids
        )
    {
        CredentialPointer[] storage ptrs = studentCredentials[studentDid];
        uint256 len = ptrs.length;

        batchIds    = new string[](len);
        leafIndices = new uint256[](len);
        ipfsCids    = new string[](len);

        for (uint256 i = 0; i < len; i++) {
            batchIds[i]    = ptrs[i].batchId;
            leafIndices[i] = ptrs[i].leafIndex;
            ipfsCids[i]    = ptrs[i].ipfsCid;
        }
    }

    // =========================================================================
    // READ: Get batch info
    // =========================================================================
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
}