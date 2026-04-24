# =============================================================================
# main.py  —  Decentralized Academic Credential Verifier
# FastAPI Backend — Rewritten for dual IPFS nodes + Hardhat, no DB/Pinata
# =============================================================================
#
# ARCHITECTURE (new stack):
#
#   ┌─────────────────────────────────────────────────────────────┐
#   │                        FastAPI (this file)                   │
#   │                                                             │
#   │  Issue:  write → IPFS Write Node (Docker :5001)            │
#   │          hash  → Hardhat / Ethereum (:8545)                │
#   │                                                             │
#   │  Verify: read  ← IPFS Read Node  (Docker :5002)            │
#   │          hash  ← Ethereum (view call, free)                │
#   │                                                             │
#   │  Student dashboard: reads from blockchain + IPFS read node  │
#   └─────────────────────────────────────────────────────────────┘
#
# NO PostgreSQL  → blockchain is the index; IPFS is the store
# NO Pinata      → self-hosted IPFS nodes in Docker
# NO Infura      → Hardhat local node (dev) or direct RPC (prod)
#
# HOW TO RUN:
#   1. docker compose up -d                     (starts IPFS + Hardhat)
#   2. cd blockchain && npm install
#   3. npx hardhat run scripts/deploy.js --network localhost
#   4. Copy CONTRACT_ADDRESS from output into .env
#   5. pip install fastapi uvicorn web3 requests python-dotenv pydantic
#   6. uvicorn main:app --reload --port 8000
# =============================================================================

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from web3 import Web3
from web3.middleware import geth_poa_middleware

import requests
from dotenv import load_dotenv

load_dotenv()
# =============================================================================
# SECTION 1: APP INITIALIZATION
# =============================================================================
# =============================================================================
# MERKLE TREE IMPLEMENTATION
# =============================================================================
import math

class MerkleTree:
    """
    A binary Merkle tree built from SHA-256 hashes.

    FORMULA RECAP:
      Leaf:    L(i)   = SHA256(credential_json_i)
      Parent:  P(i,j) = SHA256(L(i) + L(j))   ← concatenation of raw bytes
      Root:    R       = top-level parent

    ODD LEAF HANDLING:
      If a level has an odd number of nodes, duplicate the last one.
      [A, B, C] becomes [A, B, C, C] before hashing pairs.
      This ensures the tree is always a complete binary tree.

    LEAF INDEX:
      The position of a leaf in the original list (0-indexed).
      This tells the verifier whether to place the sibling on the left or right
      at each level. Even index = left child. Odd index = right child.

    PROOF SIZE:
      ceil(log2(n)) hashes.  For n=500: ceil(log2(500)) = 9 hashes.
      Compare to storing all 500 hashes = 56x more efficient.
    """

    def __init__(self, leaves: list[bytes]):
        """
        Args:
            leaves: list of 32-byte hash values (bytes objects).
                    Each is SHA-256(credential_json).
        """
        if not leaves:
            raise ValueError("Cannot build Merkle tree from empty list")

        self.leaves = leaves
        self.tree   = self._build(leaves)
        # self.tree[0]  = root
        # self.tree[-1] = list of leaf nodes (last level)

    @staticmethod
    def hash_pair(left: bytes, right: bytes) -> bytes:
        """
        Hash two sibling nodes together.
        ORDER MATTERS: left always comes first.
        The leaf index tells us which side is "left" vs "right".

        We use keccak256 (not SHA-256) here to match Solidity's
        keccak256(abi.encodePacked(left, right)).
        This lets the smart contract verify our proofs directly.
        """
        from eth_hash.auto import keccak
        return keccak(left + right)

    @staticmethod
    def sha256_leaf(data: str) -> bytes:
        """
        Hash a credential JSON string → 32 bytes (the leaf value).
        This is SHA-256 of the sorted JSON — same as hash_credential().
        Returns raw bytes (not hex string).
        """
        return hashlib.sha256(data.encode("utf-8")).digest()
        # .digest()    → raw bytes (32 bytes)
        # .hexdigest() → hex string (64 chars) — we DON'T want this for tree math

    def _build(self, leaves: list[bytes]) -> list[list[bytes]]:
        """
        Build the tree bottom-up.
        Returns a list of levels: tree[0] = [root], tree[-1] = leaves.

        ALGORITHM:
          1. Start with the leaf level
          2. Pair up adjacent nodes and hash each pair → new level
          3. If odd count, duplicate the last node before pairing
          4. Repeat until only one node remains (the root)

        Example with 4 leaves [A, B, C, D]:
          Level 2 (leaves): [A,    B,    C,    D   ]
          Level 1:          [AB,         CD         ]
          Level 0 (root):   [ABCD                   ]
        """
        current_level = leaves[:]
        levels = [current_level]

        while len(current_level) > 1:
            next_level = []

            # Duplicate last leaf if odd count (complete the binary tree)
            if len(current_level) % 2 == 1:
                current_level = current_level + [current_level[-1]]

            # Hash pairs
            for i in range(0, len(current_level), 2):
                parent = self.hash_pair(current_level[i], current_level[i + 1])
                next_level.append(parent)

            levels.insert(0, next_level)   # prepend so levels[0] = root level
            current_level = next_level

        return levels

    @property
    def root(self) -> bytes:
        """The Merkle root — 32 bytes. This is what gets stored on-chain."""
        return self.tree[0][0]

    @property
    def root_hex(self) -> str:
        """Root as a 64-char hex string."""
        return self.root.hex()

    def get_proof(self, leaf_index: int) -> list[str]:
        """
        Generate the Merkle proof for a leaf at the given index.

        The proof is the list of SIBLING hashes from leaf to root.
        The verifier uses these to reconstruct the root.

        EXAMPLE (4 leaves, proving index 0 = A):
          Leaf level: [A, B, C, D]
          Proof[0] = B  (sibling of A at leaf level)
          Proof[1] = CD (sibling of AB at level 1)

          Verifier computes:
            hash(A + B)  = AB    ← used proof[0]=B, index=0 (even) → A is left
            hash(AB + CD) = root ← used proof[1]=CD, index=0 (even) → AB is left

        Returns:
            list of hex strings (one per tree level, from leaf to root)
        """
        proof  = []
        index  = leaf_index
        levels = self.tree  # levels[0] = root, levels[-1] = leaves

        # Traverse from leaf level (last) up to root level (first), skip root
        for level in reversed(levels[:-1]):
            # Determine sibling index
            if index % 2 == 0:
                sibling_index = index + 1  # right sibling
            else:
                sibling_index = index - 1  # left sibling

            # Pad with duplicate if sibling doesn't exist (odd level)
            if sibling_index >= len(level):
                sibling = level[index]  # duplicate self (last node in odd level)
            else:
                sibling = level[sibling_index]

            proof.append(sibling.hex())
            index //= 2  # parent index at next level

        return proof

    def verify_proof(self, leaf: bytes, index: int, proof: list[bytes]) -> bool:
        """
        Verify a Merkle proof (Python-side, for testing).
        Mirrors the Solidity _verifyMerkleProof() logic exactly.

        Args:
            leaf:  the leaf hash (bytes)
            index: leaf position in the original list
            proof: list of sibling hashes (bytes) from leaf to root
        """
        computed = leaf
        for sibling in proof:
            if index % 2 == 0:
                computed = self.hash_pair(computed, sibling)  # left + right
            else:
                computed = self.hash_pair(sibling, computed)  # left + right
            index //= 2

        return computed == self.root


# =============================================================================
# IN-MEMORY BATCH STAGING (replaces PostgreSQL for pending batches)
# =============================================================================
# Credentials accumulate here until the university commits the batch.
# In production, use Redis for persistence across restarts.
#
# Structure:
#   pending_batches = {
#       "IITB-2024-GRADUATION": { as example only
#           "credentials": [
#               {"credential_data": {...}, "student_did": "...", "ipfs_cid": "..."},
#               ...
#           ]
#       }
#   }

pending_batches: dict = {}
# committed_batch_proofs stores generated proofs so students can retrieve them
# without recomputing. Structure: { batch_id: { leaf_index: [proof_hex, ...] } }
committed_batch_proofs: dict = {}

#FastAPI Main
app = FastAPI(
    title="Credential Verifier API",
    description="Academic credential system: Hardhat blockchain + dual self-hosted IPFS nodes",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://your-deployed-frontend.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# SECTION 2: IPFS CONFIGURATION (dual nodes — no Pinata)
# =============================================================================
#
# We run TWO IPFS nodes in Docker:
#
#   IPFS_WRITE_API  → where FastAPI UPLOADS credentials (POST /api/v0/add)
#                     This is the primary node. Only one writer keeps it simple.
#
#   IPFS_READ_API   → where FastAPI FETCHES credentials (GET /ipfs/<cid>)
#                     This is the replica. Employers/students read from here.
#                     If it doesn't have the content yet, IPFS will fetch from
#                     the write node (they're peered) and cache it.
#
# IPFS_WRITE_GATEWAY / IPFS_READ_GATEWAY → HTTP access to content by CID.
#   The API (port 5001) is for admin operations (pin, add, etc.)
#   The Gateway (port 8080) is for serving content publicly (GET /ipfs/CID)

IPFS_WRITE_API     = os.getenv("IPFS_WRITE_API",     "http://localhost:5001")
IPFS_READ_API      = os.getenv("IPFS_READ_API",      "http://localhost:5002")
IPFS_WRITE_GATEWAY = os.getenv("IPFS_WRITE_GATEWAY", "http://localhost:8080")
IPFS_READ_GATEWAY  = os.getenv("IPFS_READ_GATEWAY",  "http://localhost:8081")

# =============================================================================
# SECTION 3: BLOCKCHAIN SETUP (Hardhat local node)
# =============================================================================
#
# Instead of Infura/Sepolia, we connect to the Hardhat node running in Docker.
# URL: http://localhost:8545  (or http://hardhat:8545 if FastAPI is in Docker)
#
# Hardhat gives us:
#   - 10 pre-funded test accounts (1000 ETH each)
#   - Instant block mining (no 12-second wait)
#   - Free gas (testnet ETH)
#   - Full Ethereum JSON-RPC compatibility (same API as mainnet)
#
# For production: change HARDHAT_NODE_URL to your actual RPC endpoint.

HARDHAT_NODE_URL = os.getenv("HARDHAT_NODE_URL", "http://localhost:8545")

w3 = Web3(Web3.HTTPProvider(HARDHAT_NODE_URL))

# geth_poa_middleware handles the slightly different block headers used by
# some networks. Harmless to include even for Hardhat.
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

UNIVERSITY_PRIVATE_KEY = os.getenv("UNIVERSITY_PRIVATE_KEY")
UNIVERSITY_ADDRESS     = os.getenv("UNIVERSITY_ADDRESS")
CONTRACT_ADDRESS       = os.getenv("CONTRACT_ADDRESS")

# ---------------------------------------------------------------------------
# Load the ABI from a JSON file (generated by Hardhat's deploy script).
# This is cleaner than storing a giant JSON string in .env.
# The deploy script saves it to backend/contract_abi.json automatically.
# ---------------------------------------------------------------------------
_abi_path = os.path.join(os.path.dirname(__file__), "contract_abi.json")
if os.path.exists(_abi_path):
    with open(_abi_path) as f:
        CONTRACT_ABI = json.load(f)
    print(f"Loaded ABI from {_abi_path} ({len(CONTRACT_ABI)} entries)")
else:
    CONTRACT_ABI = json.loads(os.getenv("CONTRACT_ABI", "[]"))
    print("WARNING: contract_abi.json not found. Using CONTRACT_ABI env var.")

# Create the contract instance (Python object representing our smart contract).
# If CONTRACT_ADDRESS is not set yet (before first deploy), this will be None.
contract = None
if CONTRACT_ADDRESS and CONTRACT_ABI:
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
        abi=CONTRACT_ABI
    )
    # Web3.to_checksum_address() normalizes the address casing.
    # Ethereum addresses are case-insensitive but checksummed addresses
    # (mixed case) let you detect typos. Always use checksum addresses.


# =============================================================================
# SECTION 4: PYDANTIC MODELS
# =============================================================================

class IssueCredentialRequest(BaseModel):
    student_did:      str            = Field(..., example="did:ethr:0xAbC123...")
    student_name:     str            = Field(..., example="Priya Sharma")
    student_email:    str            = Field(..., example="priya@iitb.ac.in")
    university_name:  str            = Field(..., example="IIT Bombay")
    degree:           str            = Field(..., example="Bachelor of Technology")
    branch:           str            = Field(..., example="Computer Science and Engineering")
    graduation_year:  str            = Field(..., example="2024")
    cgpa:             Optional[float] = Field(None, example=8.7)


class VerifyCredentialRequest(BaseModel):
    credential_hash: str = Field(..., description="SHA-256 hex hash of the credential")


class CredentialResponse(BaseModel):
    success:         bool
    credential_hash: str
    ipfs_cid:        Optional[str]
    tx_hash:         Optional[str]
    ipfs_read_url:   Optional[str]   # URL to fetch from the READ node
    ipfs_write_url:  Optional[str]   # URL to fetch from the WRITE node
    message:         str


class VerificationResponse(BaseModel):
    is_valid:        bool
    is_revoked:      bool
    ipfs_cid:        Optional[str]
    issued_at:       Optional[str]   # ISO timestamp
    university_name: Optional[str]   # From IPFS full credential
    degree:          Optional[str]
    branch:          Optional[str]
    graduation_year: Optional[str]
    student_name:    Optional[str]
    message:         str


class StudentCredentialsResponse(BaseModel):
    student_did:  str
    credentials:  List[dict]
    total:        int

class AddToBatchRequest(BaseModel):
    batch_id:      str = Field(..., example="IITB-2024-GRADUATION")
    student_did:   str = Field(..., example="did:iitb:a3f9b2c1")
    student_name:  str
    student_email: str
    university_name: str
    degree:        str
    branch:        str
    graduation_year: str
    cgpa:          Optional[float] = None


class CommitBatchRequest(BaseModel):
    batch_id: str = Field(..., example="IITB-2024-GRADUATION")


class VerifyWithProofRequest(BaseModel):
    batch_id:        str
    credential_hash: str       
    proof:           list[str]  
    leaf_index:      int       


class BatchStatusResponse(BaseModel):
    batch_id:         str
    pending_count:    int
    is_committed:     bool
    merkle_root:      Optional[str]
    committed_at:     Optional[str]

# =============================================================================
# SECTION 5: IPFS HELPER FUNCTIONS (replaces Pinata functions)
# =============================================================================

def pin_to_ipfs_write(credential_data: dict) -> Optional[str]:
    """
    Uploads (pins) a credential JSON to our self-hosted IPFS write node.
    Returns the CID (Content Identifier) on success, None on failure.

    HOW IPFS ADD WORKS:
    1. We POST the JSON to the IPFS API (/api/v0/add)
    2. IPFS computes the content hash (CID) from the data
    3. IPFS stores the data and returns the CID
    4. "pin=true" parameter tells IPFS to pin this content permanently
       (pinned content is never garbage collected)

    DIFFERENCE FROM PINATA:
    → No API keys needed (it's our own node)
    → No rate limits
    → No monthly costs
    → Data lives on our Docker volume (we control it)
    → Peered with the read node, so content is available there too

    IPFS API DOCS: https://docs.ipfs.tech/reference/kubo/rpc/
    """
    try:
        # Convert dict to JSON string, then to bytes for multipart upload.
        credential_json = json.dumps(credential_data, sort_keys=True, indent=2)
        credential_bytes = credential_json.encode("utf-8")

        # IPFS API uses multipart form upload.
        # "files" kwarg in requests = multipart/form-data.
        response = requests.post(
            f"{IPFS_WRITE_API}/api/v0/add",
            files={"file": ("credential.json", credential_bytes, "application/json")},
            params={
                "pin": "true",           # Pin permanently (don't garbage collect)
                "cid-version": "1",      # Use CIDv1 (newer format, base32 encoded)
                # CIDv0 looks like: QmXoypizj...  (base58, starts with Qm)
                # CIDv1 looks like: bafybeig...   (base32, more web-friendly)
            },
            timeout=30,
        )
        response.raise_for_status()

        result = response.json()
        cid = result["Hash"]
        size = result.get("Size", "unknown")
        print(f"Pinned to IPFS write node. CID: {cid}, Size: {size} bytes")
        print(f"Read via write gateway: {IPFS_WRITE_GATEWAY}/ipfs/{cid}")
        return cid

    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to IPFS write node. Is Docker running?")
        print(f"Expected at: {IPFS_WRITE_API}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"IPFS upload failed: {e}")
        return None


def fetch_from_ipfs_read(cid: str) -> Optional[dict]:
    """
    Fetches credential JSON from the IPFS read node (replica).
    Falls back to the write node if the read node doesn't have it yet.

    WHY TRY READ FIRST?
    → Read node is dedicated to serving reads — no write traffic competing.
    → If we have multiple read nodes in future, this is load-balanced.
    → Write node stays focused on accepting new content.

    WHY FALLBACK TO WRITE?
    → On the very first fetch after a new credential, the read node may
      not have synced yet (IPFS peering is near-instant but not zero-latency).
    → Fallback ensures we never fail unnecessarily.
    """
    # Try read node first.
    for gateway in [IPFS_READ_GATEWAY, IPFS_WRITE_GATEWAY]:
        try:
            response = requests.get(
                f"{gateway}/ipfs/{cid}",
                timeout=15,
                headers={"Accept": "application/json"},
            )
            if response.status_code == 200:
                node_name = "read" if gateway == IPFS_READ_GATEWAY else "write"
                print(f"Fetched CID {cid} from IPFS {node_name} gateway")
                return response.json()
        except requests.exceptions.RequestException:
            continue  # Try the next gateway

    print(f"WARNING: Could not fetch CID {cid} from either IPFS node")
    return None


def pin_to_read_node(cid: str) -> bool:
    """
    Explicitly pins a CID on the read node so it has a local copy.

    NORMALLY: The read node fetches content from the write node lazily
    (on first request). This function forces an EAGER pin.

    WHY EAGER PIN?
    → Guarantees reads are always fast (served from local cache).
    → If the write node goes down temporarily, read node still serves it.
    → More robust for production use.

    In IPFS terms: pin/add tells the node to fetch and retain this CID.
    """
    try:
        response = requests.post(
            f"{IPFS_READ_API}/api/v0/pin/add",
            params={"arg": cid},
            timeout=30,
        )
        response.raise_for_status()
        print(f"CID {cid} pinned on read node successfully")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Could not pin CID on read node (non-critical): {e}")
        return False


def get_ipfs_node_id(api_url: str) -> Optional[str]:
    """Returns the peer ID of an IPFS node. Used for diagnostics."""
    try:
        response = requests.post(f"{api_url}/api/v0/id", timeout=5)
        return response.json().get("ID")
    except Exception:
        return None


# =============================================================================
# SECTION 6: BLOCKCHAIN HELPER FUNCTIONS
# =============================================================================

def hash_credential(credential_data: dict) -> str:
    """
    SHA-256 hash of the credential JSON (sorted keys for consistency).
    Returns a 64-character hex string.
    In Solidity, this maps to bytes32.
    """
    credential_json  = json.dumps(credential_data, sort_keys=True)
    credential_bytes = credential_json.encode("utf-8")
    return hashlib.sha256(credential_bytes).hexdigest()


def hex_to_bytes32(hex_str: str) -> bytes:
    """
    Converts a 64-char hex hash string to the bytes32 type that Solidity expects.

    WHY DO WE NEED THIS?
    Solidity's bytes32 is a raw 32-byte type.
    Python's web3.py needs a Python bytes object of exactly 32 bytes.
    hex_str = "a3f9b2c1..." (64 hex chars = 32 bytes)
    bytes.fromhex(hex_str) = b'\xa3\xf9\xb2\xc1...' (32 bytes)
    """
    return bytes.fromhex(hex_str)


def store_on_blockchain(student_did: str, credential_hash: str, ipfs_cid: str) -> Optional[str]:
    """
    Calls issueCredential() on the smart contract.
    Returns the transaction hash on success, None on failure.

    HARDHAT DIFFERENCES vs Infura/Sepolia:
    → URL is http://localhost:8545 (local, no API key)
    → Mining is instant (no 15-second wait for a block)
    → Gas is "free" (test ETH, pre-funded accounts)
    → Chain ID is 31337

    The actual web3.py calls are IDENTICAL to mainnet — only the URL changes.
    This is the beauty of Hardhat: drop-in replacement for development.
    """
    if not contract or not UNIVERSITY_PRIVATE_KEY:
        print("WARNING: Contract or private key not configured. Skipping blockchain.")
        return None

    try:
        checksum_address = Web3.to_checksum_address(UNIVERSITY_ADDRESS)
        nonce = w3.eth.get_transaction_count(checksum_address)

        # Convert the hex hash string → bytes32 for Solidity
        credential_hash_bytes = hex_to_bytes32(credential_hash)

        transaction = contract.functions.issueCredential(
            student_did,
            credential_hash_bytes,   # bytes32 — not a string
            ipfs_cid or "",
        ).build_transaction({
            "from":     checksum_address,
            "nonce":    nonce,
            "gas":      300_000,
            # On Hardhat, gasPrice can be 0 (or use EIP-1559 fields).
            # We use a minimal gwei to keep the call format identical to mainnet.
            "gasPrice": w3.to_wei("1", "gwei"),
        })

        signed_tx = w3.eth.account.sign_transaction(
            transaction,
            private_key=UNIVERSITY_PRIVATE_KEY,
        )

        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # On Hardhat with auto-mining, this returns almost instantly.
        # On a real network, this can take 15–30 seconds.
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60, poll_latency=0.5)

        if receipt.status == 1:
            print(f"Credential stored on blockchain. TX: {tx_hash.hex()}")
            print(f"Gas used: {receipt.gasUsed}")
            return tx_hash.hex()
        else:
            print("Transaction reverted by smart contract.")
            return None

    except Exception as e:
        print(f"Blockchain transaction failed: {e}")
        return None


def verify_on_blockchain(credential_hash: str):
    """
    Calls verifyCredential() on the smart contract (READ-ONLY, free).
    Returns (is_valid, is_revoked, ipfs_cid, issued_at) or None on error.

    VIEW FUNCTION CALL:
    → .call() executes the function locally, reading from the node's state.
    → No transaction, no gas fee, no signing needed.
    → Returns immediately (no mining to wait for).
    """
    if not contract:
        return None

    try:
        credential_hash_bytes = hex_to_bytes32(credential_hash)

        # Returns (bool isValid, bool isRevoked, string ipfsCid, uint256 issuedAt)
        result = contract.functions.verifyCredential(credential_hash_bytes).call()
        return result  # (is_valid, is_revoked, ipfs_cid, issued_at_unix)

    except Exception as e:
        print(f"Blockchain verification call failed: {e}")
        return None


def get_student_hashes_from_blockchain(student_did: str) -> list:
    """
    Fetches all credential hashes for a student from the smart contract.
    The contract maintains a mapping of studentDid → bytes32[] (array of hashes).
    """
    if not contract:
        return []

    try:
        hashes_bytes = contract.functions.getStudentCredentials(student_did).call()
        # Convert bytes32 back to hex strings for JSON response
        return [h.hex() for h in hashes_bytes]
    except Exception as e:
        print(f"getStudentCredentials call failed: {e}")
        return []


# =============================================================================
# SECTION 7: API ROUTES
# =============================================================================

# --- Health Check -------------------------------------------------------------
@app.get("/health")
def health_check():
    """
    Checks the status of all three infrastructure components:
    - Ethereum / Hardhat node
    - IPFS write node
    - IPFS read node
    """
    blockchain_ok = w3.is_connected()

    write_node_id = get_ipfs_node_id(IPFS_WRITE_API)
    read_node_id  = get_ipfs_node_id(IPFS_READ_API)

    return {
        "status": "healthy" if blockchain_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "blockchain": {
                "connected":   blockchain_ok,
                "url":         HARDHAT_NODE_URL,
                "chain_id":    w3.eth.chain_id if blockchain_ok else None,
                "contract":    CONTRACT_ADDRESS or "NOT DEPLOYED",
            },
            "ipfs_write": {
                "reachable":   write_node_id is not None,
                "peer_id":     write_node_id,
                "api":         IPFS_WRITE_API,
                "gateway":     IPFS_WRITE_GATEWAY,
            },
            "ipfs_read": {
                "reachable":   read_node_id is not None,
                "peer_id":     read_node_id,
                "api":         IPFS_READ_API,
                "gateway":     IPFS_READ_GATEWAY,
            },
        },
    }


# --- Issue Credential ---------------------------------------------------------
# @app.post("/api/credentials/issue", response_model=CredentialResponse)
# def issue_credential(
#     request: IssueCredentialRequest,
#     authorization: Optional[str] = Header(None),
# ):
#     """
#     Issues a new academic credential.

#     FLOW:
#     1. Authenticate the university
#     2. Build the W3C Verifiable Credential JSON
#     3. Hash it (SHA-256)
#     4. Upload to IPFS write node → get CID
#     5. Trigger eager pin on IPFS read node (async-ish, best effort)
#     6. Store hash + CID on Ethereum via Hardhat
#     7. Return credential_hash, CID, tx_hash to frontend
#     """

#     # --- Auth -----------------------------------------------------------------
#     expected = f"Bearer {os.getenv('API_KEY', 'dev-key')}"
#     if not authorization or authorization != expected:
#         raise HTTPException(status_code=401, detail="Invalid authorization token.")

#     # --- Build credential JSON ------------------------------------------------
#     credential_data = {
#         "@context": [
#             "https://www.w3.org/2018/credentials/v1",
#             "https://www.w3.org/2018/credentials/examples/v1",
#         ],
#         "type": ["VerifiableCredential", "UniversityDegreeCredential"],
#         "issuer": {
#             "id":   f"did:ethr:{UNIVERSITY_ADDRESS}",
#             "name": request.university_name,
#         },
#         "issuanceDate": datetime.now(timezone.utc).isoformat(),
#         "credentialSubject": {
#             "id":             request.student_did,
#             "studentName":    request.student_name,
#             "studentEmail":   request.student_email,
#             "universityName": request.university_name,
#             "degree":         request.degree,
#             "branch":         request.branch,
#             "graduationYear": request.graduation_year,
#             **({"cgpa": request.cgpa} if request.cgpa is not None else {}),
#         },
#     }

#     # --- Hash -----------------------------------------------------------------
#     credential_hash = hash_credential(credential_data)

#     # --- Duplicate check (via blockchain) ------------------------------------
#     # Instead of a DB query, we check the smart contract.
#     # This is a free read call — no gas, instant.
#     existing = verify_on_blockchain(credential_hash)
#     if existing and existing[0]:  # is_valid = True means already issued
#         raise HTTPException(
#             status_code=409,
#             detail=f"This credential has already been issued. Hash: {credential_hash}",
#         )

#     # --- Upload to IPFS write node -------------------------------------------
#     ipfs_cid = pin_to_ipfs_write(credential_data)
#     if not ipfs_cid:
#         # IPFS failed — still proceed with blockchain only.
#         # The credential_hash is on-chain; IPFS can be re-uploaded later.
#         print("WARNING: IPFS upload failed. Proceeding with blockchain only.")

#     # --- Eager pin on read node (best effort) --------------------------------
#     # Don't block the response on this — it's an optimization, not a requirement.
#     if ipfs_cid:
#         pin_to_read_node(ipfs_cid)
#         # In production, this would be a background task (FastAPI BackgroundTasks)
#         # so it doesn't add latency to the response. For simplicity, we do it
#         # synchronously here — it's fast since both nodes are Docker peers.

#     # --- Store on blockchain -------------------------------------------------
#     tx_hash = store_on_blockchain(
#         student_did=request.student_did,
#         credential_hash=credential_hash,
#         ipfs_cid=ipfs_cid or "",
#     )

#     # --- Return response -----------------------------------------------------
#     return CredentialResponse(
#         success=True,
#         credential_hash=credential_hash,
#         ipfs_cid=ipfs_cid,
#         tx_hash=tx_hash,
#         ipfs_read_url=f"{IPFS_READ_GATEWAY}/ipfs/{ipfs_cid}" if ipfs_cid else None,
#         ipfs_write_url=f"{IPFS_WRITE_GATEWAY}/ipfs/{ipfs_cid}" if ipfs_cid else None,
#         message=(
#             f"Credential issued for {request.student_name}. "
#             f"{'On IPFS + blockchain.' if tx_hash and ipfs_cid else 'Partial success — check logs.'}"
#         ),
#     )


# # --- Verify Credential --------------------------------------------------------
# @app.post("/api/credentials/verify", response_model=VerificationResponse)
# def verify_credential(request: VerifyCredentialRequest):
#     """
#     Verifies a credential hash against the blockchain.
#     If valid, fetches the full credential from IPFS read node.

#     NO AUTH REQUIRED — verification is public by design.

#     VERIFICATION LOGIC:
#     1. Ask the smart contract: does this hash exist? Is it revoked?
#        → This is the authoritative answer. The blockchain cannot lie.
#     2. If valid, fetch the full credential from IPFS read node.
#        → The IPFS data lets us show human-readable info to the employer.
#     3. Cross-check: hash the IPFS data and compare to the stored hash.
#        → If they don't match, the IPFS data was tampered with.
#        → The blockchain hash is trusted; the IPFS data must match it.
#     """

#     # --- Step 1: Blockchain verification (authoritative) ---------------------
#     blockchain_result = verify_on_blockchain(request.credential_hash)

#     if blockchain_result is None:
#         # Blockchain unreachable — cannot verify.
#         raise HTTPException(
#             status_code=503,
#             detail="Blockchain node is unreachable. Cannot verify credential at this time.",
#         )

#     is_valid, is_revoked, ipfs_cid, issued_at_unix = blockchain_result

#     if not is_valid and not is_revoked:
#         # Credential not found at all
#         return VerificationResponse(
#             is_valid=False,
#             is_revoked=False,
#             ipfs_cid=None,
#             issued_at=None,
#             university_name=None,
#             degree=None,
#             branch=None,
#             graduation_year=None,
#             student_name=None,
#             message="Credential NOT FOUND on blockchain. It may be fake or never issued.",
#         )

#     if is_revoked:
#         return VerificationResponse(
#             is_valid=False,
#             is_revoked=True,
#             ipfs_cid=ipfs_cid or None,
#             issued_at=datetime.fromtimestamp(issued_at_unix, tz=timezone.utc).isoformat() if issued_at_unix else None,
#             university_name=None,
#             degree=None,
#             branch=None,
#             graduation_year=None,
#             student_name=None,
#             message="Credential has been REVOKED by the issuing university.",
#         )

#     # --- Step 2: Fetch full credential from IPFS read node -------------------
#     full_credential = None
#     if ipfs_cid:
#         full_credential = fetch_from_ipfs_read(ipfs_cid)

#     # --- Step 3: Cross-check IPFS data integrity -----------------------------
#     if full_credential:
#         computed_hash = hash_credential(full_credential)
#         if computed_hash != request.credential_hash:
#             # The IPFS data doesn't match the blockchain hash!
#             # This means the IPFS file was tampered with (extremely rare in practice).
#             # The blockchain hash is trusted — the IPFS data is suspect.
#             return VerificationResponse(
#                 is_valid=False,
#                 is_revoked=False,
#                 ipfs_cid=ipfs_cid,
#                 issued_at=None,
#                 university_name=None,
#                 degree=None,
#                 branch=None,
#                 graduation_year=None,
#                 student_name=None,
#                 message="INTEGRITY FAILURE: IPFS data does not match blockchain hash. The credential file may be tampered.",
#             )

#     # --- Step 4: Return verified result with metadata from IPFS --------------
#     subject = full_credential.get("credentialSubject", {}) if full_credential else {}
#     issued_at_iso = (
#         datetime.fromtimestamp(issued_at_unix, tz=timezone.utc).isoformat()
#         if issued_at_unix else None
#     )

#     return VerificationResponse(
#         is_valid=True,
#         is_revoked=False,
#         ipfs_cid=ipfs_cid,
#         issued_at=issued_at_iso,
#         university_name=subject.get("universityName"),
#         degree=subject.get("degree"),
#         branch=subject.get("branch"),
#         graduation_year=subject.get("graduationYear"),
#         student_name=subject.get("studentName"),
#         # NOTE: CGPA is in the IPFS data but we don't return it here.
#         # The employer only sees basic credential info.
#         # Students share CGPA selectively using ZKPs (future feature).
#         message=f"Credential is VALID. Issued on {issued_at_iso}.",
#     )

# --- Step 1: Add credential to pending batch (no blockchain tx yet) ----------
@app.post("/api/credentials/batch/add")
def add_to_batch(
    request: AddToBatchRequest,
    authorization: Optional[str] = Header(None),
):
    """
    Stages a credential in a pending batch.
    NO blockchain transaction happens here — just IPFS upload.
    
    FLOW:
    1. Build credential JSON
    2. Upload to IPFS write node (get CID)
    3. Pin on read node
    4. Add to in-memory pending batch
    
    The university calls this for each student, then calls /batch/commit
    once to write all of them to the blockchain in one transaction.
    """
    if not authorization or authorization != f"Bearer {os.getenv('API_KEY', 'dev-key')}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Build credential JSON (same as before)
    credential_data = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", "UniversityDegreeCredential"],
        "issuer": {"id": f"did:ethr:{UNIVERSITY_ADDRESS}", "name": request.university_name},
        "issuanceDate": datetime.now(timezone.utc).isoformat(),
        "credentialSubject": {
            "id":             request.student_did,
            "studentName":    request.student_name,
            "studentEmail":   request.student_email,
            "universityName": request.university_name,
            "degree":         request.degree,
            "branch":         request.branch,
            "graduationYear": request.graduation_year,
            **({"cgpa": request.cgpa} if request.cgpa is not None else {}),
        },
    }

    # Upload to IPFS immediately (so content is available even before batch commit)
    ipfs_cid = pin_to_ipfs_write(credential_data)
    if ipfs_cid:
        pin_to_read_node(ipfs_cid)

    # Stage in pending batch
    if request.batch_id not in pending_batches:
        pending_batches[request.batch_id] = {"credentials": []}

    pending_batches[request.batch_id]["credentials"].append({
        "credential_data": credential_data,
        "student_did":     request.student_did,
        "ipfs_cid":        ipfs_cid or "",
    })

    position = len(pending_batches[request.batch_id]["credentials"]) - 1

    return {
        "success":    True,
        "batch_id":   request.batch_id,
        "leaf_index": position,
        "ipfs_cid":   ipfs_cid,
        "message":    f"Added to batch '{request.batch_id}' at position {position}. Commit when ready.",
    }


# --- Step 2: Commit the batch (ONE blockchain transaction) -------------------
@app.post("/api/credentials/batch/commit")
def commit_batch(
    request: CommitBatchRequest,
    authorization: Optional[str] = Header(None),
):
    """
    Finalizes a pending batch onto the blockchain.
    1 transaction regardless of how many credentials are in the batch.
    
    FLOW:
    1. Collect all staged credentials for this batch_id
    2. Hash each credential JSON → leaf bytes
    3. Build Merkle tree from all leaves
    4. Compute root
    5. Store proofs in memory for student retrieval
    6. Send ONE transaction to commitBatch() on the smart contract
    
    GAS SAVING:
    Old approach: 500 credentials = 500 transactions ≈ 500 * 80,000 = 40M gas
    New approach: 500 credentials = 1 transaction  ≈ 150,000 gas (fixed cost)
    Saving: ~99.6% less gas for large batches
    """
    if not authorization or authorization != f"Bearer {os.getenv('API_KEY', 'dev-key')}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    batch_id = request.batch_id

    if batch_id not in pending_batches:
        raise HTTPException(status_code=404, detail=f"No pending batch named '{batch_id}'")

    credentials = pending_batches[batch_id]["credentials"]
    if not credentials:
        raise HTTPException(status_code=400, detail="Batch is empty")

    # --- Build Merkle tree ---------------------------------------------------
    # Step 1: hash each credential JSON → raw bytes (leaf)
    leaves = []
    for cred in credentials:
        cred_json  = json.dumps(cred["credential_data"], sort_keys=True)
        leaf_bytes = MerkleTree.sha256_leaf(cred_json)
        leaves.append(leaf_bytes)

    # Step 2: build the tree
    tree = MerkleTree(leaves)
    root_hex = tree.root_hex

    print(f"Batch '{batch_id}': {len(leaves)} credentials → root {root_hex[:16]}...")
    print(f"Tree depth: {len(tree.tree) - 1} levels")

    # Step 3: generate and store all proofs
    committed_batch_proofs[batch_id] = {}
    for i in range(len(leaves)):
        committed_batch_proofs[batch_id][i] = tree.get_proof(i)

    # --- Prepare arrays for the smart contract call -------------------------
    student_dids  = [c["student_did"] for c in credentials]
    leaf_indices  = list(range(len(credentials)))
    ipfs_cids     = [c["ipfs_cid"]    for c in credentials]

    # Convert root hex → bytes32 for web3
    root_bytes32 = bytes.fromhex(root_hex)

    # --- One blockchain transaction ------------------------------------------
    if not contract or not UNIVERSITY_PRIVATE_KEY:
        print("WARNING: Contract not configured. Skipping blockchain commit.")
        tx_hash_str = None
    else:
        try:
            checksum_address = Web3.to_checksum_address(UNIVERSITY_ADDRESS)
            nonce = w3.eth.get_transaction_count(checksum_address)

            transaction = contract.functions.commitBatch(
                batch_id,
                root_bytes32,
                len(credentials),
                student_dids,
                leaf_indices,
                ipfs_cids,
            ).build_transaction({
                "from":     checksum_address,
                "nonce":    nonce,
                "gas":      500_000,   # fixed cost, NOT proportional to batch size
                "gasPrice": w3.to_wei("1", "gwei"),
            })

            signed_tx = w3.eth.account.sign_transaction(
                transaction, private_key=UNIVERSITY_PRIVATE_KEY
            )
            tx_hash     = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt     = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60, poll_latency=0.5)
            tx_hash_str = tx_hash.hex() if receipt.status == 1 else None

            print(f"Batch committed. TX: {tx_hash_str}, Gas used: {receipt.gasUsed}")

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Blockchain commit failed: {e}")

    # Clean up pending batch
    del pending_batches[batch_id]

    return {
        "success":          True,
        "batch_id":         batch_id,
        "merkle_root":      root_hex,
        "credential_count": len(credentials),
        "tx_hash":          tx_hash_str,
        "tree_depth":       len(tree.tree) - 1,
        "proof_size":       math.ceil(math.log2(max(len(leaves), 2))),
        "message": (
            f"Batch of {len(credentials)} credentials committed. "
            f"1 transaction instead of {len(credentials)}. "
            f"Root: {root_hex[:16]}..."
        ),
    }


# --- Get a student's Merkle proof (they need this to share with employers) ---
@app.get("/api/credentials/batch/{batch_id}/proof/{leaf_index}")
def get_merkle_proof(
    batch_id:   str,
    leaf_index: int,
    authorization: Optional[str] = Header(None),
):
    """
    Returns the Merkle proof for a specific credential in a committed batch.
    Students need this proof to let employers verify their credential on-chain.
    
    The proof is just a list of hex strings — small enough to include in a QR code
    or share link URL parameter.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")

    if batch_id not in committed_batch_proofs:
        raise HTTPException(status_code=404, detail=f"No committed batch '{batch_id}'")

    if leaf_index not in committed_batch_proofs[batch_id]:
        raise HTTPException(status_code=404, detail=f"Leaf index {leaf_index} not in batch")

    proof = committed_batch_proofs[batch_id][leaf_index]

    return {
        "batch_id":   batch_id,
        "leaf_index": leaf_index,
        "proof":      proof,               # list of hex strings
        "proof_size": len(proof),          # number of hashes in proof
        "message":    "Share proof + leaf_index + batch_id with employer for verification",
    }


# --- Verify using Merkle proof (replaces old verify endpoint) ----------------
@app.post("/api/credentials/verify", response_model=VerificationResponse)
def verify_credential(request: VerifyWithProofRequest):
    """
    Verifies a credential using its Merkle proof.
    
    The employer receives from the student:
      - batch_id       (which batch the credential is in)
      - credential_hash (hex hash of the credential JSON)
      - proof          (list of sibling hashes)
      - leaf_index     (position in the tree)
    
    VERIFICATION STEPS:
    1. Fetch batch root from blockchain (authoritative)
    2. Use proof to recompute root from credential_hash + siblings
    3. Compare computed root to stored root
    4. Fetch full credential from IPFS and cross-check hash
    5. Return result
    
    The smart contract does the Merkle proof verification on-chain.
    This is trustless — no need to trust our backend.
    """
    if not contract:
        raise HTTPException(status_code=503, detail="Blockchain unavailable")

    try:
        credential_hash_bytes = bytes.fromhex(request.credential_hash)
        proof_bytes = [bytes.fromhex(p) for p in request.proof]

        # Call verifyCredential() on the smart contract
        # The CONTRACT does the Merkle proof math — not our backend
        is_valid, is_revoked, committed_at = contract.functions.verifyCredential(
            request.batch_id,
            credential_hash_bytes,
            proof_bytes,
            request.leaf_index,
        ).call()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Blockchain call failed: {e}")

    if is_revoked:
        return VerificationResponse(
            is_valid=False, is_revoked=True, ipfs_cid=None,
            issued_at=None, university_name=None, degree=None,
            branch=None, graduation_year=None, student_name=None,
            message="Credential has been REVOKED.",
        )

    if not is_valid:
        return VerificationResponse(
            is_valid=False, is_revoked=False, ipfs_cid=None,
            issued_at=None, university_name=None, degree=None,
            branch=None, graduation_year=None, student_name=None,
            message="Credential NOT VALID. Proof does not match batch root.",
        )

    # Fetch full credential from IPFS read node for display
    # (We need the CID — get it from the blockchain index)
    try:
        batch_data = contract.functions.getBatch(request.batch_id).call()
        # Returns (merkleRoot, credentialCount, committedAt, isRevoked, exists)
        committed_at_unix = batch_data[2]
    except Exception:
        committed_at_unix = None

    # Get student's IPFS CID via their credential pointer
    ipfs_cid      = None
    full_credential = None
    try:
        # For simplicity, the frontend should pass the CID along with the proof.
        # Alternatively query getStudentCredentials and find matching leaf_index.
        pass
    except Exception:
        pass

    issued_at_iso = (
        datetime.fromtimestamp(committed_at_unix, tz=timezone.utc).isoformat()
        if committed_at_unix else None
    )

    return VerificationResponse(
        is_valid=True,
        is_revoked=False,
        ipfs_cid=ipfs_cid,
        issued_at=issued_at_iso,
        university_name=None,  # fetch from IPFS if CID available
        degree=None,
        branch=None,
        graduation_year=None,
        student_name=None,
        message=f"Credential VALID. Merkle proof verified on-chain. Batch: {request.batch_id}",
    )


# --- Batch status (how many pending credentials) ----------------------------
@app.get("/api/credentials/batch/{batch_id}/status")
def batch_status(batch_id: str, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Auth required")

    pending  = pending_batches.get(batch_id, {}).get("credentials", [])
    proofs   = committed_batch_proofs.get(batch_id)

    # Check blockchain for committed batch info
    on_chain = None
    if contract:
        try:
            result = contract.functions.getBatch(batch_id).call()
            if result[4]:  # exists
                on_chain = {
                    "merkle_root":      result[0].hex(),
                    "credential_count": result[1],
                    "committed_at":     datetime.fromtimestamp(result[2], tz=timezone.utc).isoformat(),
                    "is_revoked":       result[3],
                }
        except Exception:
            pass

    return {
        "batch_id":      batch_id,
        "pending_count": len(pending),
        "is_committed":  proofs is not None or on_chain is not None,
        "on_chain":      on_chain,
    }

# --- Student Credentials (from blockchain) ------------------------------------
@app.get("/api/credentials/student/{student_did}", response_model=StudentCredentialsResponse)
def get_student_credentials(
    student_did: str,
    authorization: Optional[str] = Header(None),
):
    """
    Returns all credentials for a student by querying the blockchain directly.

    NO DATABASE NEEDED:
    The smart contract maintains studentDid → bytes32[] mapping.
    We fetch the array of hashes, then verify+fetch each one.

    TRADEOFF vs PostgreSQL:
    → Slower for large numbers of credentials (N blockchain calls instead of 1 DB query)
    → But: no database to maintain, no sync issues, always accurate
    → For a student with 3-5 credentials, this is fine (milliseconds per call)
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required.")

    # Get all credential hashes for this student from the blockchain.
    hashes = get_student_hashes_from_blockchain(student_did)

    credentials_list = []
    for h in hashes:
        # For each hash, get the full on-chain record.
        result = verify_on_blockchain(h)
        if result is None:
            continue

        is_valid, is_revoked, ipfs_cid, issued_at_unix = result

        # Optionally fetch metadata from IPFS read node.
        subject = {}
        if ipfs_cid and is_valid:
            full_cred = fetch_from_ipfs_read(ipfs_cid)
            if full_cred:
                subject = full_cred.get("credentialSubject", {})

        credentials_list.append({
            "credential_hash":  h,
            "ipfs_cid":         ipfs_cid,
            "is_valid":         is_valid,
            "is_revoked":       is_revoked,
            "issued_at":        datetime.fromtimestamp(issued_at_unix, tz=timezone.utc).isoformat() if issued_at_unix else None,
            "university_name":  subject.get("universityName"),
            "degree":           subject.get("degree"),
            "branch":           subject.get("branch"),
            "graduation_year":  subject.get("graduationYear"),
            "ipfs_read_url":    f"{IPFS_READ_GATEWAY}/ipfs/{ipfs_cid}" if ipfs_cid else None,
            "ipfs_write_url":   f"{IPFS_WRITE_GATEWAY}/ipfs/{ipfs_cid}" if ipfs_cid else None,
        })

    return StudentCredentialsResponse(
        student_did=student_did,
        credentials=credentials_list,
        total=len(credentials_list),
    )


# --- Revoke Credential --------------------------------------------------------
@app.post("/api/credentials/revoke/{credential_hash}")
def revoke_credential(
    credential_hash: str,
    authorization: Optional[str] = Header(None),
):
    """
    Revokes a credential by its hash.
    Only the university (UNIVERSITY_PRIVATE_KEY holder) can do this.

    NO DATABASE UPDATE NEEDED:
    The revocation is recorded directly on the smart contract.
    Next call to verifyCredential() will return is_revoked=True.
    """
    expected = f"Bearer {os.getenv('API_KEY', 'dev-key')}"
    if not authorization or authorization != expected:
        raise HTTPException(status_code=401, detail="Only universities can revoke credentials.")

    # Check credential exists first.
    result = verify_on_blockchain(credential_hash)
    if result is None:
        raise HTTPException(status_code=503, detail="Blockchain unreachable.")

    is_valid, is_revoked, _, _ = result

    if not is_valid and not is_revoked:
        raise HTTPException(status_code=404, detail="Credential not found on blockchain.")

    if is_revoked:
        raise HTTPException(status_code=409, detail="Credential is already revoked.")

    # Call revokeCredential() on the smart contract.
    try:
        checksum_address = Web3.to_checksum_address(UNIVERSITY_ADDRESS)
        nonce = w3.eth.get_transaction_count(checksum_address)
        credential_hash_bytes = hex_to_bytes32(credential_hash)

        transaction = contract.functions.revokeCredential(
            credential_hash_bytes
        ).build_transaction({
            "from":     checksum_address,
            "nonce":    nonce,
            "gas":      100_000,
            "gasPrice": w3.to_wei("1", "gwei"),
        })

        signed_tx = w3.eth.account.sign_transaction(
            transaction, private_key=UNIVERSITY_PRIVATE_KEY
        )
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60, poll_latency=0.5)

        if receipt.status != 1:
            raise HTTPException(status_code=500, detail="Revocation transaction reverted.")

        return {
            "success": True,
            "credential_hash": credential_hash,
            "tx_hash": tx_hash.hex(),
            "message": "Credential revoked successfully on blockchain.",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Revocation failed: {str(e)}")


# --- Fetch from IPFS (convenience endpoint) -----------------------------------
@app.get("/api/ipfs/{cid}")
def get_from_ipfs(cid: str):
    """
    Fetches content from our IPFS read node and returns it.
    Falls back to write node if read node doesn't have it yet.

    Useful for the frontend to fetch full credentials without
    needing to know the IPFS gateway URLs.
    """
    data = fetch_from_ipfs_read(cid)
    if not data:
        raise HTTPException(
            status_code=502,
            detail=f"Could not fetch CID {cid} from IPFS nodes. Content may not be pinned yet.",
        )
    return {
        "cid":            cid,
        "data":           data,
        "ipfs_read_url":  f"{IPFS_READ_GATEWAY}/ipfs/{cid}",
        "ipfs_write_url": f"{IPFS_WRITE_GATEWAY}/ipfs/{cid}",
    }


# --- Generate Share Link ------------------------------------------------------
@app.get("/api/credentials/{credential_hash}/share-link")
def generate_share_link(
    credential_hash: str,
    authorization: Optional[str] = Header(None),
):
    """
    Generates a shareable link for an employer to verify a credential.
    The link encodes the credential hash — employers paste it into the verify page.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required.")

    # Confirm the credential exists on-chain before generating a link.
    result = verify_on_blockchain(credential_hash)
    if not result or (not result[0] and not result[1]):
        raise HTTPException(status_code=404, detail="Credential not found on blockchain.")

    _, _, ipfs_cid, _ = result

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    return {
        "credential_hash":    credential_hash,
        "verification_url":   f"{frontend_url}/verify?hash={credential_hash}",
        "ipfs_read_url":      f"{IPFS_READ_GATEWAY}/ipfs/{ipfs_cid}" if ipfs_cid else None,
        "ipfs_write_url":     f"{IPFS_WRITE_GATEWAY}/ipfs/{ipfs_cid}" if ipfs_cid else None,
        "instructions": (
            "Share the verification_url with employers. "
            "They can paste the hash into the verify page to check it on the blockchain."
        ),
    }


# --- IPFS Node Status ---------------------------------------------------------
@app.get("/api/ipfs/status")
def ipfs_status():
    """
    Returns detailed status of both IPFS nodes.
    Useful for monitoring and debugging.
    """
    def node_stats(api_url: str, gateway_url: str, label: str) -> dict:
        try:
            id_resp    = requests.post(f"{api_url}/api/v0/id",       timeout=5).json()
            stat_resp  = requests.post(f"{api_url}/api/v0/repo/stat", timeout=10).json()
            peers_resp = requests.post(f"{api_url}/api/v0/swarm/peers", timeout=5).json()

            return {
                "label":       label,
                "reachable":   True,
                "peer_id":     id_resp.get("ID"),
                "agent":       id_resp.get("AgentVersion"),
                "repo_size":   stat_resp.get("RepoSize"),
                "num_objects": stat_resp.get("NumObjects"),
                "peer_count":  len(peers_resp.get("Peers", [])),
                "api_url":     api_url,
                "gateway_url": gateway_url,
            }
        except Exception as e:
            return {
                "label":     label,
                "reachable": False,
                "error":     str(e),
                "api_url":   api_url,
            }

    return {
        "write_node": node_stats(IPFS_WRITE_API, IPFS_WRITE_GATEWAY, "write"),
        "read_node":  node_stats(IPFS_READ_API,  IPFS_READ_GATEWAY,  "read"),
        "timestamp":  datetime.now(timezone.utc).isoformat(),
    }


# =============================================================================
# SECTION 8: STARTUP EVENT
# =============================================================================

@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print("Credential Verifier API v2.0 starting...")
    print(f"Stack: Hardhat + dual IPFS (no PostgreSQL, no Pinata)")
    print()

    # Blockchain status
    if w3.is_connected():
        chain_id = w3.eth.chain_id
        chain_name = {31337: "Hardhat local", 11155111: "Sepolia", 1: "Mainnet"}.get(chain_id, f"Chain {chain_id}")
        print(f"Blockchain: CONNECTED ({chain_name})")
        print(f"  Node URL:       {HARDHAT_NODE_URL}")
        print(f"  Contract:       {CONTRACT_ADDRESS or 'NOT DEPLOYED — run deploy.js'}")
        print(f"  University:     {UNIVERSITY_ADDRESS or 'NOT SET'}")
        if UNIVERSITY_ADDRESS:
            try:
                balance = w3.eth.get_balance(Web3.to_checksum_address(UNIVERSITY_ADDRESS))
                print(f"  Balance:        {w3.from_wei(balance, 'ether')} ETH")
            except Exception:
                pass
    else:
        print(f"Blockchain: OFFLINE — is Hardhat running at {HARDHAT_NODE_URL}?")
        print(f"  Run: cd blockchain && npx hardhat node")

    print()

    # IPFS status
    write_id = get_ipfs_node_id(IPFS_WRITE_API)
    read_id  = get_ipfs_node_id(IPFS_READ_API)
    print(f"IPFS Write Node: {'ONLINE' if write_id else 'OFFLINE'}")
    if write_id:
        print(f"  Peer ID:  {write_id}")
        print(f"  API:      {IPFS_WRITE_API}")
        print(f"  Gateway:  {IPFS_WRITE_GATEWAY}")
    else:
        print(f"  → docker compose up ipfs-write")

    print(f"IPFS Read Node:  {'ONLINE' if read_id else 'OFFLINE'}")
    if read_id:
        print(f"  Peer ID:  {read_id}")
        print(f"  API:      {IPFS_READ_API}")
        print(f"  Gateway:  {IPFS_READ_GATEWAY}")
    else:
        print(f"  → docker compose up ipfs-read")

    print()
    print(f"API docs: http://localhost:8000/docs")
    print("=" * 60)


# =============================================================================
# SECTION 9: ENTRYPOINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
