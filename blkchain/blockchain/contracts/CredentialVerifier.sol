// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// =============================================================================
// CredentialVerifier.sol
// =============================================================================
//
// PURPOSE:
//   This smart contract is the single source of truth for academic credentials.
//   It stores credential hashes on the Ethereum blockchain — tamper-proof and
//   permanently verifiable by anyone, anywhere, without trusting any server.
//
// HOW IT FITS IN THE SYSTEM:
//   University (FastAPI) → signs transaction → this contract stores the hash
//   Employer (FastAPI)   → calls verifyCredential() → reads from this contract
//   IPFS Node (Docker)   → stores the full credential JSON (referenced by CID)
//
// ARCHITECTURE DECISION — why only store hashes on-chain?
//   Storing 1 KB of data on Ethereum costs ~$5–50 in gas fees.
//   A 32-byte hash costs ~$0.10. So we:
//     1. Store the FULL credential on IPFS (free, decentralized)
//     2. Store only the HASH + IPFS CID on-chain (cheap, tamper-proof)
//   Verification = fetch from IPFS → hash it → compare to on-chain hash.
//
// EVENTS:
//   Events are Ethereum's way of emitting logs. They're much cheaper than
//   storage. The FastAPI backend can listen for these events to react in
//   real-time (e.g., update UI when a credential is confirmed on-chain).
// =============================================================================

contract CredentialVerifier {

    // =========================================================================
    // DATA STRUCTURES
    // =========================================================================

    /**
     * @dev Represents one academic credential stored on-chain.
     *
     * We store MINIMAL data here — just enough to verify and look up.
     * The full credential (name, degree, CGPA, etc.) lives on IPFS.
     *
     * Storage costs in Solidity:
     *   - bool     → 1 byte  (but padded to 32 bytes in storage slot)
     *   - uint256  → 32 bytes
     *   - address  → 20 bytes
     *   - string   → variable (dynamic, more expensive)
     *   - bytes32  → exactly 32 bytes (fixed, cheaper than string for hashes)
     */
    struct Credential {
        string  studentDid;       // e.g., "did:ethr:0xAbC123..."
        bytes32 credentialHash;   // SHA-256 hash of the full credential JSON
        string  ipfsCid;          // IPFS Content ID — where full data lives
        address issuedBy;         // The university's Ethereum wallet address
        uint256 issuedAt;         // Unix timestamp of issuance
        bool    isRevoked;        // True if university has revoked this
        bool    exists;           // Sentinel flag — is this slot populated?
        //                          We need this because Solidity maps return
        //                          zero-value structs for missing keys (not null).
    }

    // =========================================================================
    // STATE VARIABLES
    // =========================================================================

    // The university wallet address that is ALLOWED to issue/revoke credentials.
    // Only this address can call issueCredential() and revokeCredential().
    // Set once at deployment — cannot be changed (immutable security guarantee).
    address public immutable universityAddress;

    /**
     * @dev Primary index: hash → Credential
     *
     * WHY bytes32 as key instead of string?
     * → bytes32 is a fixed-size type — cheaper and simpler for Solidity.
     * → SHA-256 hashes are always 32 bytes. Perfect fit.
     * → string keys are dynamic and more expensive to hash internally.
     *
     * Solidity mapping = like a Python dict, but:
     *   - Keys that don't exist return zero-value struct (not null/KeyError)
     *   - You can't iterate over keys (no .keys() method)
     *   - Perfectly efficient O(1) lookup by hash
     */
    mapping(bytes32 => Credential) private credentials;

    /**
     * @dev Secondary index: studentDid → list of credential hashes
     *
     * WHY store this separately?
     * → The primary map lets you look up ONE credential by hash (for verification).
     * → This secondary map lets you list ALL credentials for a student (for dashboard).
     * → Without this, you'd have to scan every credential ever issued — impossible.
     */
    mapping(string => bytes32[]) private studentCredentials;

    // Total credentials ever issued — useful for analytics and UI display.
    uint256 public totalCredentials;

    // =========================================================================
    // EVENTS
    // =========================================================================
    // Events are logged to the Ethereum transaction receipt.
    // They cost much less gas than storage and can be queried off-chain.
    // The FastAPI backend subscribes to these using web3.py's event filters.

    event CredentialIssued(
        bytes32 indexed credentialHash,  // indexed = searchable/filterable
        string  indexed studentDid,
        address indexed issuedBy,
        string  ipfsCid,
        uint256 issuedAt
    );
    // "indexed" parameters are stored in the "topics" section of the log.
    // You can filter events by indexed fields: "show me all credentials for did:ethr:0x123"
    // Non-indexed fields go in the "data" section (not filterable, but cheaper).

    event CredentialRevoked(
        bytes32 indexed credentialHash,
        address indexed revokedBy,
        uint256 revokedAt
    );

    // =========================================================================
    // MODIFIERS
    // =========================================================================
    // Modifiers are reusable checks that run BEFORE a function body.
    // They're like Python decorators for security checks.

    /**
     * @dev Restricts function access to the university address only.
     * Usage: add "onlyUniversity" after function params in the signature.
     * If the check fails, the transaction reverts — nothing is stored, no gas wasted.
     */
    modifier onlyUniversity() {
        require(
            msg.sender == universityAddress,
            "Only the university can perform this action"
            // msg.sender = the Ethereum address that signed this transaction
        );
        _;  // "_;" means "now run the actual function body"
    }

    // =========================================================================
    // CONSTRUCTOR
    // =========================================================================

    /**
     * @dev Called ONCE when the contract is deployed to the blockchain.
     *
     * @param _universityAddress The wallet address that will issue credentials.
     *
     * HOW HARDHAT CALLS THIS:
     *   In scripts/deploy.js:
     *     const contract = await CredentialVerifier.deploy(universityAddress);
     *   The address is passed as a constructor argument.
     *
     * WHY immutable?
     *   Once set, universityAddress can NEVER change. This is a security feature.
     *   If we allowed changing it, an attacker who compromises the contract owner
     *   could change the university to their own address and issue fake credentials.
     */
    constructor(address _universityAddress) {
        require(_universityAddress != address(0), "University address cannot be zero");
        // address(0) = "0x0000...0000" — the null/burn address. Never valid.
        universityAddress = _universityAddress;
    }

    // =========================================================================
    // WRITE FUNCTIONS (cost gas — modify state)
    // =========================================================================

    /**
     * @dev Issues a new academic credential on-chain.
     *
     * @param studentDid      The student's Decentralized Identifier
     * @param credentialHash  SHA-256 hash of the full credential JSON (as bytes32)
     * @param ipfsCid         IPFS Content ID where the full credential is stored
     *
     * CALLED BY: FastAPI's store_on_blockchain() function
     * SECURITY: onlyUniversity modifier ensures only IIT Bombay's wallet can call this
     * GAS COST: ~80,000–120,000 gas (writing to storage is expensive)
     *
     * WHY bytes32 for credentialHash?
     * → SHA-256 always produces exactly 32 bytes.
     * → bytes32 is a fixed-size Solidity type — no dynamic allocation overhead.
     * → Cheaper gas than string for storing hashes.
     * → In Python: bytes32 = bytes.fromhex(hash_string)
     */
    function issueCredential(
        string  calldata studentDid,
        bytes32 credentialHash,
        string  calldata ipfsCid
    ) external onlyUniversity {
        // Prevent duplicate issuance — same hash cannot be issued twice.
        require(!credentials[credentialHash].exists, "Credential already issued");
        require(bytes(studentDid).length > 0, "Student DID cannot be empty");
        require(credentialHash != bytes32(0), "Credential hash cannot be zero");

        // Store the credential in the primary mapping.
        // "storage" means this persists on the blockchain permanently.
        credentials[credentialHash] = Credential({
            studentDid:     studentDid,
            credentialHash: credentialHash,
            ipfsCid:        ipfsCid,
            issuedBy:       msg.sender,          // university's address
            issuedAt:       block.timestamp,     // current block's Unix timestamp
            isRevoked:      false,
            exists:         true
        });

        // Add to the student's credential list (secondary index).
        studentCredentials[studentDid].push(credentialHash);

        // Increment global counter.
        totalCredentials++;

        // Emit an event — logged in the transaction receipt.
        // FastAPI can listen for this to confirm issuance without polling.
        emit CredentialIssued(
            credentialHash,
            studentDid,
            msg.sender,
            ipfsCid,
            block.timestamp
        );
    }

    /**
     * @dev Revokes a previously issued credential.
     *
     * @param credentialHash  Hash of the credential to revoke
     *
     * REVOCATION IS NOT DELETION:
     *   We don't delete the record — we flip is_revoked to true.
     *   Why? Because the blockchain is immutable — you can't actually delete.
     *   Also, the audit trail of "this was issued and then revoked" is valuable.
     *   Employers can see the credential existed but was revoked.
     */
    function revokeCredential(bytes32 credentialHash) external onlyUniversity {
        require(credentials[credentialHash].exists, "Credential does not exist");
        require(!credentials[credentialHash].isRevoked, "Credential already revoked");

        credentials[credentialHash].isRevoked = true;

        emit CredentialRevoked(credentialHash, msg.sender, block.timestamp);
    }

    // =========================================================================
    // READ FUNCTIONS (free — don't modify state, no gas cost)
    // =========================================================================
    // In Solidity, "view" functions don't write to state.
    // Calling them is FREE — no transaction, no gas, instant response.
    // In web3.py: use .call() for view functions, .transact() for state changes.

    /**
     * @dev Verifies if a credential hash is valid and not revoked.
     *
     * @param credentialHash  The hash to check
     * @return isValid        True if the credential exists AND is not revoked
     * @return isRevoked      True if the credential was revoked
     * @return ipfsCid        The IPFS CID to fetch the full credential
     * @return issuedAt       Unix timestamp when it was issued
     *
     * CALLED BY: FastAPI's verify_credential() endpoint
     * GAS COST: FREE (view function, called with .call() not .transact())
     */
    function verifyCredential(bytes32 credentialHash)
        external
        view
        returns (
            bool isValid,
            bool isRevoked,
            string memory ipfsCid,
            uint256 issuedAt
        )
    {
        Credential storage cred = credentials[credentialHash];
        // "storage" reference = points directly to blockchain storage (no copy)
        // "memory" reference = makes a copy (more expensive for large structs)

        if (!cred.exists) {
            // Credential not found — return all falsy values.
            return (false, false, "", 0);
        }

        return (
            !cred.isRevoked,   // isValid = exists AND not revoked
            cred.isRevoked,
            cred.ipfsCid,
            cred.issuedAt
        );
    }

    /**
     * @dev Returns all credential hashes issued to a specific student.
     *
     * @param studentDid  The student's DID
     * @return            Array of credential hashes (bytes32[])
     *
     * CALLED BY: FastAPI's get_student_credentials() endpoint
     * NOTE: Returns hashes only — caller must fetch full data per hash using verifyCredential()
     */
    function getStudentCredentials(string calldata studentDid)
        external
        view
        returns (bytes32[] memory)
    {
        return studentCredentials[studentDid];
    }

    /**
     * @dev Returns full on-chain data for a credential (for admin/debugging).
     *
     * @param credentialHash  The hash to look up
     */
    function getCredential(bytes32 credentialHash)
        external
        view
        returns (
            string memory studentDid,
            string memory ipfsCid,
            address issuedBy,
            uint256 issuedAt,
            bool isRevoked,
            bool exists
        )
    {
        Credential storage cred = credentials[credentialHash];
        return (
            cred.studentDid,
            cred.ipfsCid,
            cred.issuedBy,
            cred.issuedAt,
            cred.isRevoked,
            cred.exists
        );
    }
}
