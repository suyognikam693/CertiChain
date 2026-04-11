# =============================================================================
# main.py  —  Decentralized Academic Credential Verifier
# FastAPI Backend — IPFS Cluster edition (replaces manual write/read nodes)
# =============================================================================
#
# ARCHITECTURE:
#
#   ┌─────────────────────────────────────────────────────────────────────┐
#   │                      FastAPI (this file)                            │
#   │                                                                     │
#   │  Issue:  POST credential ──► cluster0:9094  (IPFS Cluster REST)    │
#   │          Cluster pins to ALL nodes atomically (ipfs0 + ipfs1)      │
#   │          hash → Hardhat / Ethereum (:8545)                          │
#   │                                                                     │
#   │  Verify: read  ◄── ipfs0:8080 gateway  (or ipfs1:8082 fallback)    │
#   │          hash  ◄── Ethereum (view call, free)                       │
#   │                                                                     │
#   │  Pin status: GET cluster0:9094/pins/<cid>   (per-node status)      │
#   └─────────────────────────────────────────────────────────────────────┘
#
# WHY IPFS CLUSTER?
#   Old approach: pin to write node, then manually pin on read node.
#     - If read node is down during pin, it misses the content.
#     - No way to know if both nodes have actually pinned a CID.
#     - Custom shell scripts for peering (fragile).
#
#   IPFS Cluster:
#     - ONE API call pins to ALL nodes with Raft consensus.
#     - Cluster tracks pin status: "pinned" / "pinning" / "error" per node.
#     - Self-healing: if ipfs1 is down, cluster repins when it rejoins.
#     - No manual peering scripts — cluster manages inter-node connectivity.
#
# ENV VARS (add to .env):
#   CLUSTER_API_URL=http://localhost:9094        ← cluster0 REST API
#   CLUSTER_GATEWAY_URLS=http://localhost:8080,http://localhost:8082
#   HARDHAT_NODE_URL=http://localhost:8545
#   UNIVERSITY_PRIVATE_KEY=0x...
#   UNIVERSITY_ADDRESS=0x...
#   CONTRACT_ADDRESS=0x...
#   API_KEY=dev-key
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
from web3.middleware import ExtraDataToPOAMiddleware
import requests
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# MERKLE TREE  (unchanged from original — pure Python, no IPFS dependency)
# =============================================================================
import math

class MerkleTree:
    """
    Binary Merkle tree using keccak256 (matches Solidity's keccak256).

    Leaf:   sha256(credential_json)  → 32 bytes
    Parent: keccak256(left + right)  → 32 bytes
    Root:   top-level node           → stored on-chain as bytes32
    """

    def __init__(self, leaves: list[bytes]):
        if not leaves:
            raise ValueError("Cannot build Merkle tree from empty list")
        self.leaves = leaves
        self.tree   = self._build(leaves)

    @staticmethod
    def hash_pair(left: bytes, right: bytes) -> bytes:
        from eth_hash.auto import keccak
        return keccak(left + right)

    @staticmethod
    def sha256_leaf(data: str) -> bytes:
        return hashlib.sha256(data.encode("utf-8")).digest()

    def _build(self, leaves: list[bytes]) -> list[list[bytes]]:
        current_level = leaves[:]
        levels = [current_level]
        while len(current_level) > 1:
            if len(current_level) % 2 == 1:
                current_level = current_level + [current_level[-1]]
            next_level = [
                self.hash_pair(current_level[i], current_level[i + 1])
                for i in range(0, len(current_level), 2)
            ]
            levels.insert(0, next_level)
            current_level = next_level
        return levels

    @property
    def root(self) -> bytes:
        return self.tree[0][0]

    @property
    def root_hex(self) -> str:
        return self.root.hex()

    def get_proof(self, leaf_index: int) -> list[str]:
        proof  = []
        index  = leaf_index
        levels = self.tree
        for level in reversed(levels[:-1]):
            sibling_index = index + 1 if index % 2 == 0 else index - 1
            sibling = level[index] if sibling_index >= len(level) else level[sibling_index]
            proof.append(sibling.hex())
            index //= 2
        return proof

    def verify_proof(self, leaf: bytes, index: int, proof: list[bytes]) -> bool:
        computed = leaf
        for sibling in proof:
            computed = (
                self.hash_pair(computed, sibling) if index % 2 == 0
                else self.hash_pair(sibling, computed)
            )
            index //= 2
        return computed == self.root


# =============================================================================
# IN-MEMORY BATCH STAGING
# =============================================================================
pending_batches: dict = {}
committed_batch_proofs: dict = {}


# =============================================================================
# FASTAPI APP
# =============================================================================
app = FastAPI(
    title="Credential Verifier API",
    description="Academic credential system: Hardhat + IPFS Cluster (2 nodes)",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-deployed-frontend.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# SECTION 2: IPFS CLUSTER CONFIGURATION
# =============================================================================
#
# We now talk to ONE endpoint: the IPFS Cluster REST API (cluster0).
# Cluster internally fans out pins to all nodes (ipfs0 + ipfs1).
#
# CLUSTER REST API:
#   POST /add                  → upload + pin content on all nodes
#   GET  /pins                 → list all pinned CIDs and their status
#   GET  /pins/<cid>           → status of a specific CID
#   DELETE /pins/<cid>         → unpin from all nodes
#   GET  /id                   → this peer's cluster identity
#   GET  /peers                → all cluster peers and their status
#
# GATEWAYS:
#   We still read content through the Kubo HTTP gateways (port 8080/8082).
#   The Cluster API is write-only (add/pin/unpin).
#   For reads, both ipfs0 and ipfs1 serve the same content (both pinned).

CLUSTER_API_URL = os.getenv("CLUSTER_API_URL", "http://localhost:9094")

# Comma-separated list of Kubo gateway URLs for fetching content.
# We try them in order; first success wins.
_gateway_env = os.getenv("CLUSTER_GATEWAY_URLS", "http://localhost:8080,http://localhost:8082")
IPFS_GATEWAYS: list[str] = [g.strip() for g in _gateway_env.split(",") if g.strip()]


# =============================================================================
# SECTION 3: BLOCKCHAIN SETUP (unchanged)
# =============================================================================

HARDHAT_NODE_URL       = os.getenv("HARDHAT_NODE_URL",       "http://localhost:8545")
UNIVERSITY_PRIVATE_KEY = os.getenv("UNIVERSITY_PRIVATE_KEY")
UNIVERSITY_ADDRESS     = os.getenv("UNIVERSITY_ADDRESS")
CONTRACT_ADDRESS       = os.getenv("CONTRACT_ADDRESS")

w3 = Web3(Web3.HTTPProvider(HARDHAT_NODE_URL))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
_abi_path = os.path.join(os.path.dirname(__file__), "contract_abi.json")
if os.path.exists(_abi_path):
    with open(_abi_path) as f:
        CONTRACT_ABI = json.load(f)
    print(f"Loaded ABI from {_abi_path} ({len(CONTRACT_ABI)} entries)")
else:
    CONTRACT_ABI = json.loads(os.getenv("CONTRACT_ABI", "[]"))
    print("WARNING: contract_abi.json not found. Using CONTRACT_ABI env var.")

contract = None
if CONTRACT_ADDRESS and CONTRACT_ABI:
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
        abi=CONTRACT_ABI,
    )


# =============================================================================
# SECTION 4: PYDANTIC MODELS (unchanged from original)
# =============================================================================

class IssueCredentialRequest(BaseModel):
    student_did:      str             = Field(..., example="did:ethr:0xAbC123...")
    student_name:     str             = Field(..., example="Priya Sharma")
    student_email:    str             = Field(..., example="priya@iitb.ac.in")
    university_name:  str             = Field(..., example="IIT Bombay")
    degree:           str             = Field(..., example="Bachelor of Technology")
    branch:           str             = Field(..., example="Computer Science and Engineering")
    graduation_year:  str             = Field(..., example="2024")
    cgpa:             Optional[float] = Field(None, example=8.7)


class VerifyCredentialRequest(BaseModel):
    credential_hash: str = Field(..., description="SHA-256 hex hash of the credential")


class CredentialResponse(BaseModel):
    success:         bool
    credential_hash: str
    ipfs_cid:        Optional[str]
    tx_hash:         Optional[str]
    ipfs_gateway_url: Optional[str]   # URL via any live gateway
    message:         str


class VerificationResponse(BaseModel):
    is_valid:        bool
    is_revoked:      bool
    ipfs_cid:        Optional[str]
    issued_at:       Optional[str]
    university_name: Optional[str]
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
    batch_id:        str             = Field(..., example="IITB-2024-GRADUATION")
    student_did:     str             = Field(..., example="did:iitb:a3f9b2c1")
    student_name:    str
    student_email:   str
    university_name: str
    degree:          str
    branch:          str
    graduation_year: str
    cgpa:            Optional[float] = None


class CommitBatchRequest(BaseModel):
    batch_id: str = Field(..., example="IITB-2024-GRADUATION")


class VerifyWithProofRequest(BaseModel):
    batch_id:        str
    credential_hash: str
    proof:           list[str]
    leaf_index:      int


class BatchStatusResponse(BaseModel):
    batch_id:      str
    pending_count: int
    is_committed:  bool
    merkle_root:   Optional[str]
    committed_at:  Optional[str]


# =============================================================================
# SECTION 5: IPFS CLUSTER HELPER FUNCTIONS
# =============================================================================

def pin_to_cluster(credential_data: dict) -> Optional[str]:
    """
    Uploads content to IPFS Cluster and pins it atomically on ALL nodes.

    HOW IT DIFFERS FROM THE OLD pin_to_ipfs_write():
      Old: POST to ipfs-write:5001/api/v0/add  → pin on write node only.
           Then separately POST to ipfs-read:5002/api/v0/pin/add → pin on read.
           If read node is down: content is NOT pinned there (silently missed).

      New: POST to cluster0:9094/add  (IPFS Cluster REST API)
           Cluster handles pinning on ALL members with Raft consensus.
           If ipfs1 is down: cluster queues the pin and repins when ipfs1 returns.
           Pin status is tracked and queryable (not fire-and-forget).

    CLUSTER /add ENDPOINT:
      Unlike Kubo's /api/v0/add (which stores + pins in one step), the
      Cluster /add endpoint uploads content to one IPFS node first, then
      instructs ALL cluster peers to pin that CID.

      The response includes the CID and the allocation (which peers will pin).

    REPLICATION FACTOR:
      Set in docker-compose.yml via CLUSTER_REPLICATIONFACTORMIN/MAX = -1.
      -1 means ALL cluster peers must pin this CID.

    Returns the CID string on success, None on failure.
    """
    try:
        credential_json  = json.dumps(credential_data, sort_keys=True, indent=2)
        credential_bytes = credential_json.encode("utf-8")

        # IPFS Cluster's /add endpoint accepts multipart just like Kubo's /api/v0/add.
        # It uploads the content AND pins it across all cluster peers in one call.
        response = requests.post(
            f"{CLUSTER_API_URL}/add",
            files={
                "file": ("credential.json", credential_bytes, "application/json")
            },
            params={
                "cid-version":  "1",          # CIDv1 (bafybeig... format)
                "pin":          "true",        # Pin on commit (default, but explicit)
                "replication":  "-1",          # Override: all peers must pin
                "name":         "credential",  # Human-readable label in cluster UI
            },
            timeout=30,
        )
        response.raise_for_status()

        result = response.json()
        # Cluster /add returns: {"cid": {"/":" bafybeig..."}, "name": "credential", ...}
        # The CID is nested under the "/" key (IPFS CID JSON format).
        cid = result.get("cid", {}).get("/") or result.get("Hash") or result.get("cid")
        if not cid:
            print(f"ERROR: Unexpected cluster /add response: {result}")
            return None

        print(f"Pinned via IPFS Cluster. CID: {cid}")
        print(f"Allocation: {result.get('peer_map', 'see /pins/<cid> for status')}")
        return cid

    except requests.exceptions.ConnectionError:
        print(f"ERROR: Cannot connect to IPFS Cluster API at {CLUSTER_API_URL}.")
        print("Is cluster0 running? docker compose up -d cluster0")
        return None
    except requests.exceptions.RequestException as e:
        print(f"IPFS Cluster pin failed: {e}")
        return None


def get_cluster_pin_status(cid: str) -> Optional[dict]:
    """
    Returns the pin status of a CID across all cluster peers.

    The response shows per-peer status, e.g.:
      {
        "cid": {"/" :"bafybeig..."},
        "peer_map": {
          "12D3KooWXxx": {"peername": "cluster0", "status": "pinned",  "error": ""},
          "12D3KooWYyy": {"peername": "cluster1", "status": "pinned",  "error": ""},
        }
      }

    Status values: "pinned" | "pinning" | "pin_queued" | "remote" | "error" | "unpinned"

    "pinned"     = successfully pinned on this peer's IPFS node.
    "pinning"    = in progress (large files may take time).
    "pin_queued" = waiting to start (peer may be busy or temporarily offline).
    "error"      = pin failed — check the "error" field for details.
    """
    try:
        response = requests.get(
            f"{CLUSTER_API_URL}/pins/{cid}",
            timeout=10,
        )
        if response.status_code == 404:
            return None  # CID not known to cluster
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Could not get cluster pin status for {cid}: {e}")
        return None


def fetch_from_ipfs_gateways(cid: str) -> Optional[dict]:
    """
    Fetches credential JSON from any live IPFS gateway.

    We try each configured gateway in order (ipfs0, then ipfs1).
    Since BOTH nodes pin all content (via cluster), either gateway can serve it.
    First success wins — no fallback needed in steady state.

    This replaces fetch_from_ipfs_read() which hard-coded read vs write nodes.
    """
    for gateway in IPFS_GATEWAYS:
        try:
            response = requests.get(
                f"{gateway}/ipfs/{cid}",
                timeout=15,
                headers={"Accept": "application/json"},
            )
            if response.status_code == 200:
                print(f"Fetched CID {cid} from gateway {gateway}")
                return response.json()
        except requests.exceptions.RequestException:
            continue

    print(f"WARNING: Could not fetch CID {cid} from any gateway: {IPFS_GATEWAYS}")
    return None


def get_cluster_peer_id() -> Optional[str]:
    """Returns the cluster peer ID of cluster0. Used for diagnostics."""
    try:
        response = requests.get(f"{CLUSTER_API_URL}/id", timeout=5)
        return response.json().get("id")
    except Exception:
        return None


# =============================================================================
# SECTION 6: BLOCKCHAIN HELPER FUNCTIONS (unchanged from original)
# =============================================================================

def hash_credential(credential_data: dict) -> str:
    credential_json  = json.dumps(credential_data, sort_keys=True)
    credential_bytes = credential_json.encode("utf-8")
    return hashlib.sha256(credential_bytes).hexdigest()


def hex_to_bytes32(hex_str: str) -> bytes:
    return bytes.fromhex(hex_str)


def store_on_blockchain(student_did: str, credential_hash: str, ipfs_cid: str) -> Optional[str]:
    if not contract or not UNIVERSITY_PRIVATE_KEY:
        print("WARNING: Contract or private key not configured. Skipping blockchain.")
        return None
    try:
        checksum_address      = Web3.to_checksum_address(UNIVERSITY_ADDRESS)
        nonce                 = w3.eth.get_transaction_count(checksum_address)
        credential_hash_bytes = hex_to_bytes32(credential_hash)

        transaction = contract.functions.issueCredential(
            student_did,
            credential_hash_bytes,
            ipfs_cid or "",
        ).build_transaction({
            "from":     checksum_address,
            "nonce":    nonce,
            "gas":      300_000,
            "gasPrice": w3.to_wei("1", "gwei"),
        })

        signed_tx = w3.eth.account.sign_transaction(transaction, private_key=UNIVERSITY_PRIVATE_KEY)
        tx_hash   = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt   = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60, poll_latency=0.5)

        if receipt.status == 1:
            print(f"Stored on blockchain. TX: {tx_hash.hex()}")
            return tx_hash.hex()
        else:
            print("Transaction reverted.")
            return None
    except Exception as e:
        print(f"Blockchain transaction failed: {e}")
        return None


def verify_on_blockchain(credential_hash: str):
    if not contract:
        return None
    try:
        return contract.functions.verifyCredential(hex_to_bytes32(credential_hash)).call()
    except Exception as e:
        print(f"Blockchain verify call failed: {e}")
        return None


def get_student_hashes_from_blockchain(student_did: str) -> list:
    if not contract:
        return []
    try:
        hashes_bytes = contract.functions.getStudentCredentials(student_did).call()
        return [h.hex() for h in hashes_bytes]
    except Exception as e:
        print(f"getStudentCredentials failed: {e}")
        return []


# =============================================================================
# SECTION 7: API ROUTES
# =============================================================================

# --- Health Check -------------------------------------------------------------
@app.get("/health")
def health_check():
    """
    Returns status of Ethereum node + IPFS Cluster + all cluster peers.
    """
    blockchain_ok = w3.is_connected()

    # Check cluster REST API
    cluster_ok    = False
    cluster_peers = []
    try:
        peers_resp = requests.get(f"{CLUSTER_API_URL}/peers", timeout=5)
        if peers_resp.status_code == 200:
            cluster_ok    = True
            cluster_peers = peers_resp.json()
    except Exception:
        pass

    # Check each gateway
    gateway_status = {}
    for gw in IPFS_GATEWAYS:
        try:
            r = requests.get(f"{gw}/api/v0/id", timeout=3)
            # Kubo's gateway doesn't expose /api/v0/id, use the API port check instead.
            # We just check if the gateway root responds.
            gateway_status[gw] = "reachable"
        except Exception:
            gateway_status[gw] = "unreachable"

    overall = "healthy" if (blockchain_ok and cluster_ok) else "degraded"

    return {
        "status":    overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "blockchain": {
                "connected": blockchain_ok,
                "url":       HARDHAT_NODE_URL,
                "chain_id":  w3.eth.chain_id if blockchain_ok else None,
                "contract":  CONTRACT_ADDRESS or "NOT DEPLOYED",
            },
            "ipfs_cluster": {
                "reachable":   cluster_ok,
                "api_url":     CLUSTER_API_URL,
                "peer_count":  len(cluster_peers),
                "peers":       [
                    {
                        "id":       p.get("id"),
                        "name":     p.get("peername"),
                        "version":  p.get("version"),
                    }
                    for p in cluster_peers
                ],
            },
            "ipfs_gateways": gateway_status,
        },
    }


# --- Step 1: Add credential to pending batch ----------------------------------
@app.post("/api/credentials/batch/add")
def add_to_batch(
    request: AddToBatchRequest,
    authorization: Optional[str] = Header(None),
):
    """
    Stages a credential in a pending batch.

    FLOW (cluster edition):
    1. Build credential JSON
    2. POST to cluster0:9094/add  → pins on ALL nodes atomically
    3. Add to in-memory pending batch

    KEY DIFFERENCE FROM OLD VERSION:
    Old: pin_to_ipfs_write() + pin_to_read_node()  (two separate calls, fragile)
    New: pin_to_cluster()                            (one call, atomic, tracked)
    """
    if not authorization or authorization != f"Bearer {os.getenv('API_KEY', 'dev-key')}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    credential_data = {
        "@context":  ["https://www.w3.org/2018/credentials/v1"],
        "type":      ["VerifiableCredential", "UniversityDegreeCredential"],
        "issuer":    {"id": f"did:ethr:{UNIVERSITY_ADDRESS}", "name": request.university_name},
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

    # One call pins on ALL cluster nodes — no separate read-node pin needed.
    ipfs_cid = pin_to_cluster(credential_data)

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
        # Optionally show pin status (check cluster0 has acknowledged it)
        "pin_status_url": f"{CLUSTER_API_URL}/pins/{ipfs_cid}" if ipfs_cid else None,
        "message":    f"Added to batch '{request.batch_id}' at position {position}. Commit when ready.",
    }


# --- Step 2: Commit the batch -------------------------------------------------
@app.post("/api/credentials/batch/commit")
def commit_batch(
    request: CommitBatchRequest,
    authorization: Optional[str] = Header(None),
):
    """
    Finalizes a pending batch onto the blockchain (Merkle root commit).

    IPFS CLUSTER CHANGE:
    Nothing changes in the Merkle/blockchain logic.
    All content was already pinned on ALL nodes during /batch/add.
    The commit is purely a blockchain operation.

    GAS SAVING (same as before):
      N credentials = 1 transaction (fixed cost ~150,000 gas).
    """
    if not authorization or authorization != f"Bearer {os.getenv('API_KEY', 'dev-key')}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    batch_id    = request.batch_id
    if batch_id not in pending_batches:
        raise HTTPException(status_code=404, detail=f"No pending batch '{batch_id}'")

    credentials = pending_batches[batch_id]["credentials"]
    if not credentials:
        raise HTTPException(status_code=400, detail="Batch is empty")

    # Build Merkle tree
    leaves = [
        MerkleTree.sha256_leaf(json.dumps(c["credential_data"], sort_keys=True))
        for c in credentials
    ]
    tree     = MerkleTree(leaves)
    root_hex = tree.root_hex

    print(f"Batch '{batch_id}': {len(leaves)} credentials → root {root_hex[:16]}...")

    # Store proofs for student retrieval
    committed_batch_proofs[batch_id] = {
        i: tree.get_proof(i) for i in range(len(leaves))
    }

    student_dids = [c["student_did"] for c in credentials]
    leaf_indices = list(range(len(credentials)))
    ipfs_cids    = [c["ipfs_cid"]    for c in credentials]
    root_bytes32 = bytes.fromhex(root_hex)

    # One blockchain transaction
    tx_hash_str = None
    if contract and UNIVERSITY_PRIVATE_KEY:
        try:
            checksum_address = Web3.to_checksum_address(UNIVERSITY_ADDRESS)
            nonce            = w3.eth.get_transaction_count(checksum_address)
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
                "gas":      500_000,
                "gasPrice": w3.to_wei("1", "gwei"),
            })
            signed_tx   = w3.eth.account.sign_transaction(transaction, private_key=UNIVERSITY_PRIVATE_KEY)
            tx_hash     = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt     = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60, poll_latency=0.5)
            tx_hash_str = tx_hash.hex() if receipt.status == 1 else None
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Batch commit transaction failed: {e}")
    else:
        print("WARNING: Contract not configured. Skipping blockchain commit.")

    # Clean up pending batch
    del pending_batches[batch_id]

    return {
        "success":          True,
        "batch_id":         batch_id,
        "credential_count": len(credentials),
        "merkle_root":      root_hex,
        "tx_hash":          tx_hash_str,
        "message": (
            f"Batch '{batch_id}' committed. {len(credentials)} credentials, "
            f"root={root_hex[:16]}... All content already pinned on all IPFS nodes."
        ),
    }


# --- Verify with Merkle proof -------------------------------------------------
@app.post("/api/credentials/verify-with-proof", response_model=VerificationResponse)
def verify_with_proof(request: VerifyWithProofRequest):
    """
    Verifies a credential using its Merkle proof (on-chain verification).
    Unchanged from original — IPFS Cluster does not affect verification logic.
    """
    if not contract:
        raise HTTPException(status_code=503, detail="Blockchain unavailable")

    try:
        credential_hash_bytes = bytes.fromhex(request.credential_hash)
        proof_bytes           = [bytes.fromhex(p) for p in request.proof]

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

    issued_at_iso = (
        datetime.fromtimestamp(committed_at, tz=timezone.utc).isoformat()
        if committed_at else None
    )

    return VerificationResponse(
        is_valid=True,
        is_revoked=False,
        ipfs_cid=None,
        issued_at=issued_at_iso,
        university_name=None,
        degree=None,
        branch=None,
        graduation_year=None,
        student_name=None,
        message=f"Credential VALID. Merkle proof verified on-chain. Batch: {request.batch_id}",
    )


# --- Batch status -------------------------------------------------------------
@app.get("/api/credentials/batch/{batch_id}/status")
def batch_status(batch_id: str, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Auth required")

    pending = pending_batches.get(batch_id, {}).get("credentials", [])
    proofs  = committed_batch_proofs.get(batch_id)

    on_chain = None
    if contract:
        try:
            result = contract.functions.getBatch(batch_id).call()
            if result[4]:
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


# --- Student credentials ------------------------------------------------------
@app.get("/api/credentials/student/{student_did}", response_model=StudentCredentialsResponse)
def get_student_credentials(student_did: str, authorization: Optional[str] = Header(None)):
    """
    Returns all credentials for a student.

    IPFS CLUSTER CHANGE:
    Old version returned separate ipfs_read_url and ipfs_write_url.
    Now we return a single ipfs_url using any live gateway — content is
    identical on all nodes because cluster ensures full replication.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required.")

    hashes = get_student_hashes_from_blockchain(student_did)

    credentials_list = []
    for h in hashes:
        result = verify_on_blockchain(h)
        if result is None:
            continue

        is_valid, is_revoked, ipfs_cid, issued_at_unix = result
        subject = {}
        if ipfs_cid and is_valid:
            full_cred = fetch_from_ipfs_gateways(ipfs_cid)
            if full_cred:
                subject = full_cred.get("credentialSubject", {})

        # Single gateway URL — any live IPFS node serves the same content.
        gateway_url = f"{IPFS_GATEWAYS[0]}/ipfs/{ipfs_cid}" if ipfs_cid and IPFS_GATEWAYS else None

        credentials_list.append({
            "credential_hash": h,
            "ipfs_cid":        ipfs_cid,
            "is_valid":        is_valid,
            "is_revoked":      is_revoked,
            "issued_at":       datetime.fromtimestamp(issued_at_unix, tz=timezone.utc).isoformat() if issued_at_unix else None,
            "university_name": subject.get("universityName"),
            "degree":          subject.get("degree"),
            "branch":          subject.get("branch"),
            "graduation_year": subject.get("graduationYear"),
            "ipfs_url":        gateway_url,
        })

    return StudentCredentialsResponse(
        student_did=student_did,
        credentials=credentials_list,
        total=len(credentials_list),
    )


# --- Revoke credential --------------------------------------------------------
@app.post("/api/credentials/revoke/{credential_hash}")
def revoke_credential(credential_hash: str, authorization: Optional[str] = Header(None)):
    """
    Revokes a credential on-chain. IPFS Cluster is not involved — revocation
    is a blockchain-only operation. The credential file on IPFS is NOT deleted
    (IPFS content is immutable by CID). The on-chain flag is the authority.
    """
    if not authorization or authorization != f"Bearer {os.getenv('API_KEY', 'dev-key')}":
        raise HTTPException(status_code=401, detail="Only universities can revoke credentials.")

    result = verify_on_blockchain(credential_hash)
    if result is None:
        raise HTTPException(status_code=503, detail="Blockchain unreachable.")

    is_valid, is_revoked, _, _ = result
    if not is_valid and not is_revoked:
        raise HTTPException(status_code=404, detail="Credential not found on blockchain.")
    if is_revoked:
        raise HTTPException(status_code=409, detail="Credential is already revoked.")

    try:
        checksum_address      = Web3.to_checksum_address(UNIVERSITY_ADDRESS)
        nonce                 = w3.eth.get_transaction_count(checksum_address)
        credential_hash_bytes = hex_to_bytes32(credential_hash)

        transaction = contract.functions.revokeCredential(
            credential_hash_bytes
        ).build_transaction({
            "from":     checksum_address,
            "nonce":    nonce,
            "gas":      100_000,
            "gasPrice": w3.to_wei("1", "gwei"),
        })

        signed_tx = w3.eth.account.sign_transaction(transaction, private_key=UNIVERSITY_PRIVATE_KEY)
        tx_hash   = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt   = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60, poll_latency=0.5)

        if receipt.status != 1:
            raise HTTPException(status_code=500, detail="Revocation transaction reverted.")

        return {
            "success":         True,
            "credential_hash": credential_hash,
            "tx_hash":         tx_hash.hex(),
            "message":         "Credential revoked on blockchain.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Revocation failed: {str(e)}")


# --- Fetch from IPFS ----------------------------------------------------------
@app.get("/api/ipfs/{cid}")
def get_from_ipfs(cid: str):
    """
    Fetches content from any live IPFS gateway.
    Since cluster ensures all nodes pin all content, any gateway works.
    """
    data = fetch_from_ipfs_gateways(cid)
    if not data:
        raise HTTPException(
            status_code=502,
            detail=f"Could not fetch CID {cid} from any IPFS gateway. Content may still be pinning.",
        )
    return {
        "cid":          cid,
        "data":         data,
        "gateway_urls": [f"{gw}/ipfs/{cid}" for gw in IPFS_GATEWAYS],
        # Check cluster pin status to see if all nodes have pinned it:
        "pin_status_url": f"{CLUSTER_API_URL}/pins/{cid}",
    }


# --- IPFS Cluster status ------------------------------------------------------
@app.get("/api/ipfs/cluster/status")
def cluster_status():
    """
    Returns detailed status of the IPFS Cluster and all its peers.

    Replaces the old /api/ipfs/status endpoint which reported write/read node
    separately. Now we report the unified cluster state.
    """
    try:
        id_resp    = requests.get(f"{CLUSTER_API_URL}/id",    timeout=5).json()
        peers_resp = requests.get(f"{CLUSTER_API_URL}/peers", timeout=5).json()
    except Exception as e:
        return {
            "reachable": False,
            "error":     str(e),
            "api_url":   CLUSTER_API_URL,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "reachable":  True,
        "api_url":    CLUSTER_API_URL,
        "this_peer":  {
            "id":      id_resp.get("id"),
            "name":    id_resp.get("peername"),
            "version": id_resp.get("version"),
        },
        "peers":      [
            {
                "id":      p.get("id"),
                "name":    p.get("peername"),
                "version": p.get("version"),
                "ipfs":    p.get("ipfs", {}),
            }
            for p in peers_resp
        ],
        "gateways":   IPFS_GATEWAYS,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
    }


# --- Share link ---------------------------------------------------------------
@app.get("/api/credentials/{credential_hash}/share-link")
def generate_share_link(
    credential_hash: str,
    authorization:   Optional[str] = Header(None),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required.")

    result = verify_on_blockchain(credential_hash)
    if not result or (not result[0] and not result[1]):
        raise HTTPException(status_code=404, detail="Credential not found on blockchain.")

    _, _, ipfs_cid, _ = result
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Any gateway serves the same content — return all of them.
    ipfs_urls = [f"{gw}/ipfs/{ipfs_cid}" for gw in IPFS_GATEWAYS] if ipfs_cid else []

    return {
        "credential_hash":  credential_hash,
        "verification_url": f"{frontend_url}/verify?hash={credential_hash}",
        "ipfs_urls":        ipfs_urls,
        "instructions":     "Share verification_url with employers. They paste the hash to verify on-chain.",
    }


# =============================================================================
# SECTION 8: STARTUP EVENT
# =============================================================================

@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print("Credential Verifier API v3.0 starting (IPFS Cluster edition)...")
    print()

    if w3.is_connected():
        chain_id   = w3.eth.chain_id
        chain_name = {31337: "Hardhat local", 11155111: "Sepolia", 1: "Mainnet"}.get(chain_id, f"Chain {chain_id}")
        print(f"Blockchain: CONNECTED ({chain_name})")
        print(f"  Node URL: {HARDHAT_NODE_URL}")
        print(f"  Contract: {CONTRACT_ADDRESS or 'NOT DEPLOYED'}")
    else:
        print(f"Blockchain: OFFLINE — is Hardhat running at {HARDHAT_NODE_URL}?")

    print()

    cluster_peer_id = get_cluster_peer_id()
    print(f"IPFS Cluster: {'ONLINE' if cluster_peer_id else 'OFFLINE'}")
    if cluster_peer_id:
        print(f"  Peer ID:  {cluster_peer_id}")
        print(f"  API:      {CLUSTER_API_URL}")
        try:
            peers = requests.get(f"{CLUSTER_API_URL}/peers", timeout=5).json()
            print(f"  Cluster peers: {len(peers)}")
            for p in peers:
                print(f"    - {p.get('peername', '?')} ({p.get('id', '?')[:20]}...)")
        except Exception:
            pass
    else:
        print(f"  → docker compose up cluster0 cluster1")

    print()
    print(f"IPFS Gateways: {IPFS_GATEWAYS}")
    print(f"API docs: http://localhost:8000/docs")
    print("=" * 60)


# =============================================================================
# SECTION 9: ENTRYPOINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)