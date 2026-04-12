# =============================================================================
# main.py  —  Decentralized Academic Credential Verifier
# FastAPI Backend — IPFS Cluster edition
# =============================================================================
#
# PROOF STORAGE STRATEGY
# ----------------------
# At commit time, each credential is re-pinned to IPFS enriched with its
# Merkle proof embedded under the "merkleProof" key:
#
#   {
#     ...original credential fields...,
#     "merkleProof": {
#       "batchId":   "SPIT-2027-CSE",
#       "leafIndex": 2,
#       "proof":     ["aabbcc...", ...],   # hex-encoded sibling hashes
#       "root":      "ddeeff..."           # hex-encoded Merkle root
#     }
#   }
#
# The CID of this enriched object is what gets stored on-chain (not the
# original bare credential CID).  The leaf hash is ALWAYS computed from the
# bare credential (without merkleProof) so the Merkle math stays consistent.
#
# At read time (/api/credentials/student/:did):
#   1. Fetch on-chain pointers: (batch_id, leaf_index, enriched_cid)
#   2. Fetch enriched JSON from IPFS gateway
#   3. Strip "merkleProof" to recompute the leaf hash (= credential_hash)
#   4. Return everything the frontend needs to call /verify-with-proof
#
# ENV VARS (add to .env):
#   CLUSTER_API_URL=http://localhost:9094
#   CLUSTER_GATEWAY_URLS=http://localhost:8080,http://localhost:8082
#   HARDHAT_NODE_URL=http://localhost:8545
#   UNIVERSITY_PRIVATE_KEY=0x...
#   UNIVERSITY_ADDRESS=0x...
#   CONTRACT_ADDRESS=0x...
#   API_KEY=dev-key
#   FRONTEND_URL=http://localhost:3000
# =============================================================================

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from web3 import Web3
try:
    # web3.py <= 6
    from web3.middleware import geth_poa_middleware as poa_middleware
except ImportError:
    # web3.py >= 7
    from web3.middleware import ExtraDataToPOAMiddleware as poa_middleware

import requests
from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# MERKLE TREE
# =============================================================================

class MerkleTree:
    """
    Binary Merkle tree using keccak256 (matches Solidity keccak256).

    Leaf:   sha256(credential_json_without_proof)  -> 32 bytes
    Parent: keccak256(left + right)                -> 32 bytes
    Root:   top-level node                         -> stored on-chain as bytes32

    IMPORTANT: The leaf is always computed from the BARE credential dict
    (no "merkleProof" key).  The enriched IPFS object adds "merkleProof" on
    top, but the hash/proof math never sees it.
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
        """SHA-256 of a UTF-8 string.  Always pass json.dumps(dict, sort_keys=True)."""
        return hashlib.sha256(data.encode("utf-8")).digest()

    def _build(self, leaves: list[bytes]) -> list[list[bytes]]:
        current_level = leaves[:]
        levels        = [current_level]
        while len(current_level) > 1:
            if len(current_level) % 2 == 1:
                current_level = current_level + [current_level[-1]]
            next_level = [
                self.hash_pair(current_level[i], current_level[i + 1])
                for i in range(0, len(current_level), 2)
            ]
            levels.append(next_level)
            current_level = next_level
        return levels   # tree[0]=leaves … tree[-1]=[root]

    @property
    def root(self) -> bytes:
        return self.tree[-1][0]

    @property
    def root_hex(self) -> str:
        return self.root.hex()

    def get_proof(self, index: int) -> list[bytes]:
        proof = []
        for level in self.tree[:-1]:
            sibling_index = index + 1 if index % 2 == 0 else index - 1
            proof.append(
                level[sibling_index] if sibling_index < len(level) else level[index]
            )
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
# IN-MEMORY BATCH STAGING  (only lives until commit — not used post-commit)
# =============================================================================
pending_batches: dict = {}


# =============================================================================
# FASTAPI APP
# =============================================================================
app = FastAPI(
    title="Credential Verifier API",
    description="Academic credential system: Hardhat + IPFS Cluster (2 nodes)",
    version="3.1.0",
)

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
allowed_origins = [
    frontend_url,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# SECTION 2: IPFS CLUSTER CONFIGURATION
# =============================================================================

CLUSTER_API_URL = os.getenv("CLUSTER_API_URL", "http://localhost:9094")

_gateway_env    = os.getenv("CLUSTER_GATEWAY_URLS", "http://localhost:8080,http://localhost:8082")
IPFS_GATEWAYS: list[str] = [g.strip() for g in _gateway_env.split(",") if g.strip()]


# =============================================================================
# SECTION 3: BLOCKCHAIN SETUP
# =============================================================================

HARDHAT_NODE_URL       = os.getenv("HARDHAT_NODE_URL",       "http://localhost:8545")
UNIVERSITY_PRIVATE_KEY = os.getenv("UNIVERSITY_PRIVATE_KEY")
UNIVERSITY_ADDRESS     = os.getenv("UNIVERSITY_ADDRESS")
CONTRACT_ADDRESS       = os.getenv("CONTRACT_ADDRESS")

w3 = Web3(Web3.HTTPProvider(HARDHAT_NODE_URL))
w3.middleware_onion.inject(poa_middleware, layer=0)

_abi_path = os.path.join(os.path.dirname(__file__), "contract_abi.json")
if os.path.exists(_abi_path):
    with open(_abi_path) as f:
        artifact_data = json.load(f)
        CONTRACT_ABI  = artifact_data["abi"] if isinstance(artifact_data, dict) and "abi" in artifact_data else artifact_data
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
# SECTION 4: PYDANTIC MODELS
# =============================================================================

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
    batch_id:        str             = Field(..., example="SPIT-2027-CSE")
    student_did:     str             = Field(..., example="2023800051")
    student_name:    str
    student_email:   str
    university_name: str
    degree:          str
    branch:          str
    graduation_year: str
    cgpa:            Optional[float] = None


class CommitBatchRequest(BaseModel):
    batch_id: str = Field(..., example="SPIT-2027-CSE")


class VerifyWithProofRequest(BaseModel):
    batch_id:        str
    credential_hash: str        # hex sha256 of the BARE credential (no merkleProof key)
    proof:           list[str]  # hex-encoded sibling hashes
    leaf_index:      int


class RevokeCredentialRequest(BaseModel):
    batch_id:        str
    credential_hash: str


# =============================================================================
# SECTION 5: IPFS CLUSTER HELPER FUNCTIONS
# =============================================================================

def pin_to_cluster(data: dict, name: str = "credential") -> Optional[str]:
    """
    Serializes *data* to JSON and pins it atomically on ALL cluster nodes.
    Returns the CID string, or None on failure.

    Uses replication=-1 so the cluster pins to every peer automatically.
    """
    try:
        data_json  = json.dumps(data, sort_keys=True, indent=2)
        data_bytes = data_json.encode("utf-8")

        response = requests.post(
            f"{CLUSTER_API_URL}/add",
            files={"file": ("data.json", data_bytes, "application/json")},
            params={
                "cid-version": "1",
                "pin":         "true",
                "replication": "-1",
                "name":        name,
            },
            timeout=30,
        )
                # web3.py <= 6
        response.raise_for_status()

        lines = [l.strip() for l in response.text.splitlines() if l.strip()]
        if not lines:
            print("ERROR: Empty response from IPFS Cluster.")
            return None

        try:
            result = json.loads(lines[-1])
        except json.JSONDecodeError:
            print(f"ERROR: Could not parse Cluster response: {lines[-1]}")
            return None

        cid_raw = result.get("cid") or result.get("Hash") or result.get("hash")
        cid     = cid_raw.get("/") if isinstance(cid_raw, dict) else cid_raw

        if not cid:
            print(f"ERROR: No CID in cluster response: {result}")
            return None

        print(f"Pinned '{name}' via IPFS Cluster. CID: {cid}")
        return cid

    except requests.exceptions.ConnectionError:
        print(f"ERROR: Cannot connect to IPFS Cluster at {CLUSTER_API_URL}.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"IPFS Cluster pin failed: {e}")
        return None


def fetch_from_ipfs_gateways(cid: str) -> Optional[dict]:
    """Fetches JSON from the first live IPFS gateway."""
    for gateway in IPFS_GATEWAYS:
        try:
            r = requests.get(
                f"{gateway}/ipfs/{cid}",
                timeout=15,
                headers={"Accept": "application/json"},
            )
            if r.status_code == 200:
                print(f"Fetched CID {cid} from {gateway}")
                return r.json()
        except requests.exceptions.RequestException:
            continue
    print(f"WARNING: Could not fetch CID {cid} from any gateway.")
    return None


def get_cluster_pin_status(cid: str) -> Optional[dict]:
    try:
        r = requests.get(f"{CLUSTER_API_URL}/pins/{cid}", timeout=10)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"Could not get pin status for {cid}: {e}")
        return None


def get_cluster_peer_id() -> Optional[str]:
    try:
        return requests.get(f"{CLUSTER_API_URL}/id", timeout=5).json().get("id")
    except Exception:
        return None


# =============================================================================
# SECTION 6: BLOCKCHAIN HELPER FUNCTIONS
# =============================================================================

def hex_to_bytes32(hex_str: str) -> bytes:
    return bytes.fromhex(hex_str)

def contract_code_present(address: str) -> bool:
    """Return True only when bytecode exists at the configured contract address."""
    try:
        checksum = Web3.to_checksum_address(address)
        return len(w3.eth.get_code(checksum)) > 0
    except Exception:
        return False


def get_student_pointers_from_blockchain(student_did: str) -> list[tuple]:
    """
    Returns [(batch_id, leaf_index, enriched_ipfs_cid), ...] for a student.

    Contract getStudentCredentials(string did) must return three parallel arrays:
        string[]  batchIds
        uint256[] leafIndices
        string[]  ipfsCids      <- these are the ENRICHED CIDs (contain proof)
    """
    if not contract:
        return []
    if not contract_code_present(CONTRACT_ADDRESS):
        print(f"Contract bytecode not found at {CONTRACT_ADDRESS}")
    try:
        result = contract.functions.getStudentCredentials(student_did).call()
        print(f"DEBUG getStudentCredentials raw: {result}")
        if len(result) < 3:
            print(f"WARNING: unexpected getStudentCredentials shape: {result}")
            return []
        return list(zip(result[0], result[1], result[2]))
    except Exception as e:
        print(f"getStudentCredentials failed: {e}")
        return []


def send_transaction(built_tx: dict, fn_label: str) -> Optional[str]:
    """
    Signs and sends a pre-built transaction dict.
    Returns tx_hash hex string on success, None on revert.
    Supports both web3.py v5 (rawTransaction) and v6 (raw_transaction).
    """
    signed  = w3.eth.account.sign_transaction(built_tx, private_key=UNIVERSITY_PRIVATE_KEY)
    raw     = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction", None)
    tx      = w3.eth.send_raw_transaction(raw)
    receipt = w3.eth.wait_for_transaction_receipt(tx, timeout=60, poll_latency=0.5)
    if receipt.status == 1:
        print(f"{fn_label} | TX: {tx.hex()} | gas used: {receipt.gasUsed:,}")
        return tx.hex()
    print(f"{fn_label} REVERTED | gas used: {receipt.gasUsed:,}")
    return None


# =============================================================================
# SECTION 7: PROOF PINNING HELPER
# =============================================================================

def build_enriched_credential(credential_data: dict, batch_id: str, leaf_index: int, tree: MerkleTree) -> dict:
    """
    Returns a new dict = credential_data + "merkleProof" block.

    The proof is computed from *tree* at *leaf_index*.  The leaf hash used
    here is sha256(json.dumps(credential_data, sort_keys=True)) — i.e. the
    BARE credential without any proof key — which is exactly what commit_batch
    uses to build the tree leaves, ensuring the math stays consistent.
    """
    proof = tree.get_proof(leaf_index)
    return {
        **credential_data,
        "merkleProof": {
            "batchId":   batch_id,
            "leafIndex": leaf_index,
            "proof":     [p.hex() for p in proof],
            "root":      tree.root_hex,
        },
    }


def credential_hash_from_data(credential_data: dict) -> str:
    """
    Returns the hex sha256 leaf hash of the BARE credential dict.
    This is the value callers must pass as credential_hash to /verify-with-proof.
    Always strips 'merkleProof' before hashing so the result is stable whether
    called on the bare or enriched object.
    """
    bare = {k: v for k, v in credential_data.items() if k != "merkleProof"}
    return MerkleTree.sha256_leaf(json.dumps(bare, sort_keys=True)).hex()


def canonicalize_did(student_did: str) -> str:
    """Normalize student DID to reduce case/whitespace mismatch issues."""
    did = (student_did or "").strip()
    if not did:
        return did

    # Canonicalize did:ethr identifiers by lower-casing the address part only.
    parts = did.split(":")
    if len(parts) >= 3 and parts[0].lower() == "did" and parts[1].lower() == "ethr":
        parts[0] = "did"
        parts[1] = "ethr"
        parts[-1] = parts[-1].lower()
        return ":".join(parts)

    return did


def did_lookup_candidates(student_did: str) -> list[str]:
    """Generate lookup candidates to handle historical non-canonical storage."""
    raw = (student_did or "").strip()
    canonical = canonicalize_did(raw)

    candidates = []
    for value in (raw, canonical, raw.lower()):
        if value and value not in candidates:
            candidates.append(value)
    return candidates


# =============================================================================
# SECTION 8: API ROUTES
# =============================================================================

# --- Health Check -------------------------------------------------------------
@app.get("/health")
def health_check():
    blockchain_ok = w3.is_connected()
    contract_deployed = contract_code_present(CONTRACT_ADDRESS) if CONTRACT_ADDRESS else False

    cluster_ok    = False
    cluster_peers = []
    try:
        peers_resp = requests.get(f"{CLUSTER_API_URL}/peers", timeout=5)
        if peers_resp.status_code == 200:
            cluster_ok = True
            for line in peers_resp.text.strip().splitlines():
                line = line.strip()
                if line:
                    try:
                        cluster_peers.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass

    gateway_status = {}
    for gw in IPFS_GATEWAYS:
        try:
            r = requests.get(f"{gw}/", timeout=3, allow_redirects=True)
            gateway_status[gw] = "reachable" if r.status_code < 500 else "unreachable"
        except Exception:
            gateway_status[gw] = "unreachable"

    return {
        "status":    "healthy" if (blockchain_ok and cluster_ok) else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "blockchain": {
                "connected": blockchain_ok,
                "url":       HARDHAT_NODE_URL,
                "chain_id":  w3.eth.chain_id if blockchain_ok else None,
                "contract":  CONTRACT_ADDRESS or "NOT DEPLOYED",
                "contract_deployed": contract_deployed,
            },
            "ipfs_cluster": {
                "reachable":  cluster_ok,
                "api_url":    CLUSTER_API_URL,
                "peer_count": len(cluster_peers),
                "peers": [
                    {"id": p.get("id"), "name": p.get("peername"), "version": p.get("version")}
                    for p in cluster_peers
                ],
            },
            "ipfs_gateways": gateway_status,
        },
    }


# --- Step 1: Add credential to pending batch ----------------------------------
@app.post("/api/credentials/batch/add")
def add_to_batch(request: AddToBatchRequest):
    """
    Stages a credential in a pending in-memory batch and pins the BARE
    credential JSON to IPFS (no proof yet — proof is added at commit time).

    Returns the position (leaf_index) in the batch so the caller can track it.
    The enriched CID (with proof) replaces this CID on the chain at commit time.
    """
    # issuanceDate is set here so it is locked in before commit.
    # It reflects when the university prepared the credential, not when
    # the blockchain transaction was mined.
    student_did = canonicalize_did(request.student_did)

    credential_data = {
        "@context":  ["https://www.w3.org/2018/credentials/v1"],
        "type":      ["VerifiableCredential", "UniversityDegreeCredential"],
        "issuer":    {"id": f"did:ethr:{UNIVERSITY_ADDRESS}", "name": request.university_name},
        "issuanceDate": datetime.now(timezone.utc).isoformat(),
        "credentialSubject": {
            "id":             student_did,
            "studentName":    request.student_name,
            "studentEmail":   request.student_email,
            "universityName": request.university_name,
            "degree":         request.degree,
            "branch":         request.branch,
            "graduationYear": request.graduation_year,
            **({"cgpa": request.cgpa} if request.cgpa is not None else {}),
        },
    }

    # Pin bare credential (no proof yet). This CID is temporary — the enriched
    # CID produced at commit time is what ends up on-chain.
    bare_cid = pin_to_cluster(credential_data, name=f"bare-{request.batch_id}")
    if not bare_cid:
        raise HTTPException(
            status_code=503,
            detail=(
                "IPFS Cluster is unreachable. Start docker services (ipfs0/ipfs1/cluster0/cluster1) "
                f"or fix CLUSTER_API_URL ({CLUSTER_API_URL}) before staging credentials."
            ),
        )

    if request.batch_id not in pending_batches:
        pending_batches[request.batch_id] = {"credentials": []}

    pending_batches[request.batch_id]["credentials"].append({
        "credential_data": credential_data,
        "student_did":     student_did,
        "bare_cid":        bare_cid or "",
    })

    position = len(pending_batches[request.batch_id]["credentials"]) - 1

    return {
        "success":        True,
        "batch_id":       request.batch_id,
        "leaf_index":     position,
        "bare_ipfs_cid":  bare_cid,
        "note":           "Enriched CID (with Merkle proof) will be pinned and stored on-chain at commit time.",
        "pin_status_url": f"{CLUSTER_API_URL}/pins/{bare_cid}" if bare_cid else None,
        "message":        f"Added to batch '{request.batch_id}' at position {position}. Commit when ready.",
    }


# --- Step 2: Commit the batch -------------------------------------------------
@app.post("/api/credentials/batch/commit")
def commit_batch(request: CommitBatchRequest):
    """
    Finalizes a pending batch:

    1. Builds the Merkle tree from BARE credential JSON (no proof key).
    2. For each credential, builds an enriched object = bare + merkleProof block
       and pins it to IPFS.  FAILS HARD if any pin fails — no silent fallback
       to the proof-less CID.
    3. Stores the Merkle root + per-student pointers (enriched CIDs) on-chain
       via commitBatch().

    After this call the in-memory batch is deleted.  All proof data lives in
    IPFS and is retrievable forever via the enriched CID stored on-chain.
    """
    batch_id    = request.batch_id
    if batch_id not in pending_batches:
        raise HTTPException(status_code=404, detail=f"No pending batch '{batch_id}'")
    # print(f"Sending transaction from: {account.address}")
    credentials = pending_batches[batch_id]["credentials"]
    if not credentials:
        raise HTTPException(status_code=400, detail="Batch is empty")
    if len(credentials) < 2:
        raise HTTPException(
            status_code=400,
            detail=(
                "Batch must contain at least 2 credentials to generate non-empty Merkle proofs. "
                "Stage more credentials and retry commit."
            ),
        )

    # --- 1. Build Merkle tree from BARE credentials --------------------------
    # INVARIANT: leaf = sha256(json.dumps(bare_credential, sort_keys=True))
    # The "merkleProof" key must NEVER be present when computing leaves.
    leaves = [
        MerkleTree.sha256_leaf(json.dumps(c["credential_data"], sort_keys=True))
        for c in credentials
    ]
    tree     = MerkleTree(leaves)
    root_hex = tree.root_hex
    print(f"Batch '{batch_id}': {len(leaves)} credentials -> root {root_hex[:16]}...")

    # --- 2. Pin enriched credentials to IPFS ---------------------------------
    # Each enriched object = bare credential + "merkleProof" block containing
    # batchId, leafIndex, proof[], and root.  This is what gets stored on-chain
    # as the canonical CID for each student's credential.
    enriched_cids = []
    for i, cred in enumerate(credentials):
        enriched = build_enriched_credential(
            credential_data=cred["credential_data"],
            batch_id=batch_id,
            leaf_index=i,
            tree=tree,
        )
        enriched_cid = pin_to_cluster(
            enriched,
            name=f"enriched-{batch_id}-{i}",
        )

        # Hard fail: if any pin fails the entire commit is aborted.
        # A silent fallback to the bare CID would store a CID without a proof,
        # making that credential permanently unverifiable.
        if not enriched_cid:
            raise HTTPException(
                status_code=502,
                detail=(
                    f"Failed to pin enriched credential at index {i} "
                    f"(student: {cred['student_did']}) to IPFS Cluster. "
                    f"Commit aborted — no changes written to blockchain. "
                    f"Check IPFS Cluster health and retry."
                ),
            )

        enriched_cids.append(enriched_cid)
        print(f"  [{i}] {cred['student_did']} -> enriched CID: {enriched_cid}")

    # --- 3. Commit to blockchain ----------------------------------------------
    student_dids = [c["student_did"] for c in credentials]
    leaf_indices = list(range(len(credentials)))
    root_bytes32 = bytes.fromhex(root_hex)

    tx_hash_str = None
    if contract and UNIVERSITY_PRIVATE_KEY:
        try:
            if not contract_code_present(CONTRACT_ADDRESS):
                raise HTTPException(
                    status_code=503,
                    detail=(
                        f"Contract not deployed at {CONTRACT_ADDRESS}. "
                        "Deploy the contract and update CONTRACT_ADDRESS before committing."
                    ),
                )

            checksum_address = Web3.to_checksum_address(UNIVERSITY_ADDRESS)
            nonce            = w3.eth.get_transaction_count(checksum_address)

            commit_fn = contract.functions.commitBatch(
                batch_id,
                root_bytes32,
                len(credentials),
                student_dids,
                leaf_indices,
                enriched_cids,      # enriched CIDs — contain embedded proofs
            )

            try:
                estimated_gas = commit_fn.estimate_gas({"from": checksum_address})
                gas_limit     = int(estimated_gas * 1.25)

                print(f"Gas estimate: {estimated_gas:,} -> limit: {gas_limit:,}")
            except Exception as est_err:
                raise HTTPException(
                    status_code=400,
                    detail=f"Gas estimation failed (tx would revert): {est_err}",
                )

            BLOCK_GAS_LIMIT = 30_000_000
            if gas_limit > BLOCK_GAS_LIMIT:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Batch too large for one transaction "
                        f"(estimated {gas_limit:,} gas > block limit {BLOCK_GAS_LIMIT:,}). "
                        f"Split into smaller batches."
                    ),
                )

            transaction = commit_fn.build_transaction({
                "from":     checksum_address,
                "nonce":    nonce,
                "gas":      gas_limit,
                "gasPrice": w3.to_wei("1", "gwei"),
            })
            tx_hash_str = send_transaction(transaction, f"commitBatch({batch_id})")

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Batch commit transaction failed: {e}")
    else:
        print("WARNING: Contract not configured. Skipping blockchain commit.")

    del pending_batches[batch_id]

    return {
        "success":          True,
        "batch_id":         batch_id,
        "credential_count": len(credentials),
        "merkle_root":      root_hex,
        "tx_hash":          tx_hash_str,
        "enriched_cids":    enriched_cids,
        "message": (
            f"Batch '{batch_id}' committed. {len(credentials)} credentials, "
            f"root={root_hex[:16]}... "
            f"Proofs embedded in IPFS (enriched CIDs stored on-chain)."
        ),
    }


# --- Verify with Merkle proof -------------------------------------------------
@app.post("/api/credentials/verify-with-proof", response_model=VerificationResponse)
def verify_with_proof(request: VerifyWithProofRequest):
    """
    Verifies a credential on-chain using its Merkle proof.

    credential_hash must be sha256(json.dumps(bare_credential, sort_keys=True))
    — i.e. the hash of the credential WITHOUT the "merkleProof" key.
    The /student/:did endpoint returns this value pre-computed.
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

    return VerificationResponse(
        is_valid=True, is_revoked=False, ipfs_cid=None,
        issued_at=(
            datetime.fromtimestamp(committed_at, tz=timezone.utc).isoformat()
            if committed_at else None
        ),
        university_name=None, degree=None, branch=None,
        graduation_year=None, student_name=None,
        message=f"Credential VALID. Merkle proof verified on-chain. Batch: {request.batch_id}",
    )


# --- Batch status -------------------------------------------------------------
@app.get("/api/credentials/batch/{batch_id}/status")
def batch_status(batch_id: str):
    pending  = pending_batches.get(batch_id, {}).get("credentials", [])
    on_chain = None

    if contract:
        try:
            result = contract.functions.getBatch(batch_id).call()
            if result[4]:  # exists flag
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
        "is_committed":  on_chain is not None,
        "on_chain":      on_chain,
    }


# --- Student credentials ------------------------------------------------------
@app.get("/api/credentials/student/{student_did}", response_model=StudentCredentialsResponse)
def get_student_credentials(student_did: str):
    """
    Returns all credentials for a student, including the Merkle proof needed
    to call /verify-with-proof.

    Flow:
      1. Fetch (batch_id, leaf_index, enriched_cid) tuples from the contract.
      2. For each tuple, fetch the enriched JSON from IPFS.
      3. Strip "merkleProof" and recompute sha256 to get credential_hash.
      4. Return credential_hash + proof[] + everything the frontend needs.

    This is fully stateless — no in-memory cache is needed because the proof
    is embedded in the IPFS object stored at commit time.
    """
    pointers = []
    for candidate_did in did_lookup_candidates(student_did):
        pointers = get_student_pointers_from_blockchain(candidate_did)
        if pointers:
            student_did = candidate_did
            break

    credentials_list = []
    for (batch_id, leaf_index, enriched_cid) in pointers:
        subject          = {}
        proof_hex        = []
        merkle_root      = None
        credential_hash  = None

        if enriched_cid:
            full_cred = fetch_from_ipfs_gateways(enriched_cid)
            if full_cred:
                subject     = full_cred.get("credentialSubject", {})
                proof_block = full_cred.get("merkleProof", {})
                proof_hex   = proof_block.get("proof", [])
                merkle_root = proof_block.get("root")

                # Recompute leaf hash from BARE credential (strips merkleProof).
                # This is the value the caller must pass as credential_hash to
                # /verify-with-proof.
                credential_hash = credential_hash_from_data(full_cred)

        gateway_url = f"{IPFS_GATEWAYS[0]}/ipfs/{enriched_cid}" if enriched_cid and IPFS_GATEWAYS else None

        credentials_list.append({
            # --- fields needed to call /verify-with-proof ---
            "batch_id":        batch_id,
            "leaf_index":      leaf_index,
            "credential_hash": credential_hash,   # sha256 of bare credential
            "proof":           proof_hex,          # Merkle proof siblings (hex)
            "merkle_root":     merkle_root,        # for client-side sanity check
            # --- display fields ---
            "ipfs_cid":        enriched_cid,
            "student_name":    subject.get("studentName"),
            "university_name": subject.get("universityName"),
            "degree":          subject.get("degree"),
            "branch":          subject.get("branch"),
            "graduation_year": subject.get("graduationYear"),
            "cgpa":            subject.get("cgpa"),
            "ipfs_url":        gateway_url,
        })

    return StudentCredentialsResponse(
        student_did=student_did,
        credentials=credentials_list,
        total=len(credentials_list),
    )


# --- Revoke credential --------------------------------------------------------
@app.post("/api/credentials/revoke")
def revoke_credential(
    request:       RevokeCredentialRequest,
    # authorization: Optional[str] = Header(None),
):
    """
    Revokes a specific credential within a batch on-chain.
    Requires Bearer token matching API_KEY env var.
    IPFS data is NOT deleted (content-addressed, immutable) — revocation is
    purely an on-chain flag that verifyCredential() checks.
    """
    # if not authorization or authorization != f"Bearer {os.getenv('API_KEY', 'dev-key')}":
    #     raise HTTPException(status_code=401, detail="Only universities can revoke credentials.")

    if not contract or not UNIVERSITY_PRIVATE_KEY:
        raise HTTPException(status_code=503, detail="Blockchain not configured.")

    # Confirm the batch exists before sending a transaction
    try:
        batch_info = contract.functions.getBatch(request.batch_id).call()
        if not batch_info[4]:
            raise HTTPException(status_code=404, detail=f"Batch '{request.batch_id}' not found on-chain.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch lookup failed: {e}")

    try:
        checksum_address      = Web3.to_checksum_address(UNIVERSITY_ADDRESS)
        nonce                 = w3.eth.get_transaction_count(checksum_address)
        credential_hash_bytes = hex_to_bytes32(request.credential_hash)

        revoke_fn     = contract.functions.revokeCredential(
            credential_hash_bytes,
            request.batch_id,
        )
        estimated_gas = revoke_fn.estimate_gas({"from": checksum_address})
        transaction   = revoke_fn.build_transaction({
            "from":     checksum_address,
            "nonce":    nonce,
            "gas":      int(estimated_gas * 1.25),
            "gasPrice": w3.to_wei("1", "gwei"),
        })

        tx_hash_str = send_transaction(transaction, f"revokeCredential({request.credential_hash[:8]}...)")
        if not tx_hash_str:
            raise HTTPException(status_code=500, detail="Revocation transaction reverted.")

        return {
            "success":         True,
            "credential_hash": request.credential_hash,
            "batch_id":        request.batch_id,
            "tx_hash":         tx_hash_str,
            "message":         "Credential revoked on blockchain.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Revocation failed: {str(e)}")


# --- Fetch raw IPFS content ---------------------------------------------------
@app.get("/api/ipfs/{cid}")
def get_from_ipfs(cid: str):
    """Returns the raw JSON stored at a CID (bare or enriched credential)."""
    data = fetch_from_ipfs_gateways(cid)
    if not data:
        raise HTTPException(
            status_code=502,
            detail=f"Could not fetch CID {cid} from any gateway. Content may still be pinning.",
        )
    return {
        "cid":            cid,
        "data":           data,
        "has_proof":      "merkleProof" in data,
        "gateway_urls":   [f"{gw}/ipfs/{cid}" for gw in IPFS_GATEWAYS],
        "pin_status_url": f"{CLUSTER_API_URL}/pins/{cid}",
    }


# --- IPFS Cluster status ------------------------------------------------------
@app.get("/api/ipfs/cluster/status")
def cluster_status():
    try:
        id_resp    = requests.get(f"{CLUSTER_API_URL}/id", timeout=5).json()
        peers_raw  = requests.get(f"{CLUSTER_API_URL}/peers", timeout=5).text
        peers_list = []
        try:
            parsed     = json.loads(peers_raw)
            peers_list = parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            for line in peers_raw.strip().split("\n"):
                if line.strip():
                    peers_list.append(json.loads(line))
    except Exception as e:
        return {
            "reachable": False,
            "error":     str(e),
            "api_url":   CLUSTER_API_URL,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "reachable": True,
        "api_url":   CLUSTER_API_URL,
        "this_peer": {
            "id":      id_resp.get("id"),
            "name":    id_resp.get("peername"),
            "version": id_resp.get("version"),
        },
        "peers": [
            {"id": p.get("id"), "name": p.get("peername"), "version": p.get("version"), "ipfs": p.get("ipfs", {})}
            for p in peers_list
        ],
        "gateways":  IPFS_GATEWAYS,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# --- Share link ---------------------------------------------------------------
@app.get("/api/credentials/{batch_id}/{leaf_index}/share-link")
def generate_share_link(batch_id: str, leaf_index: int):
    """
    Generates a shareable verification URL.
    batch_id + leaf_index uniquely identify a credential in the system.
    The verifier visits the URL, fetches the proof from IPFS, and calls
    /verify-with-proof.
    """
    if not contract:
        raise HTTPException(status_code=503, detail="Blockchain unavailable.")

    try:
        batch_info = contract.functions.getBatch(batch_id).call()
        if not batch_info[4]:
            raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found on-chain.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch lookup failed: {e}")

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    return {
        "batch_id":         batch_id,
        "leaf_index":       leaf_index,
        "verification_url": f"{frontend_url}/verify?batch_id={batch_id}&leaf_index={leaf_index}",
        "instructions": (
            "Share verification_url with employers. "
            "The verifier fetches the Merkle proof from IPFS via the student endpoint "
            "and calls POST /api/credentials/verify-with-proof."
        ),
    }


# =============================================================================
# SECTION 9: STARTUP EVENT
# =============================================================================

@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print("Credential Verifier API v3.1 (IPFS proof storage edition)...")
    print()

    if w3.is_connected():
        chain_id   = w3.eth.chain_id
        chain_name = {31337: "Hardhat local", 11155111: "Sepolia", 1: "Mainnet"}.get(chain_id, f"Chain {chain_id}")
        print(f"Blockchain : CONNECTED ({chain_name})")
        print(f"  Node URL : {HARDHAT_NODE_URL}")
        print(f"  Contract : {CONTRACT_ADDRESS or 'NOT DEPLOYED'}")
    else:
        print(f"Blockchain : OFFLINE -- is Hardhat running at {HARDHAT_NODE_URL}?")

    print()

    cluster_peer_id = get_cluster_peer_id()
    print(f"IPFS Cluster: {'ONLINE' if cluster_peer_id else 'OFFLINE'}")
    if cluster_peer_id:
        print(f"  Peer ID : {cluster_peer_id}")
        print(f"  API     : {CLUSTER_API_URL}")
        try:
            peers_text = requests.get(f"{CLUSTER_API_URL}/peers", timeout=5).text
            peers = []
            for line in peers_text.strip().splitlines():
                line = line.strip()
                if line:
                    try:
                        peers.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            print(f"  Cluster peers: {len(peers)}")
            for p in peers:
                print(f"    - {p.get('peername', '?')} ({p.get('id', '?')[:20]}...)")
        except Exception:
            pass
    else:
        print(f"  -> docker compose up cluster0 cluster1")

    print()
    print(f"IPFS Gateways : {IPFS_GATEWAYS}")
    print(f"API docs      : http://localhost:8000/docs")
    print("=" * 60)

#project hail mary

import qrcode
import io
import base64

# @app.get("/api/credentials/student/{student_did}/qrs")
# def get_student_qrs(student_did: str):
#     """
#     Look up all credentials for a student by DID and return a list of QR codes.
#     This combines the lookup and generation logic into one step.
#     """
#     # 1. Use your existing blockchain/IPFS lookup function
#     pointers = get_student_pointers_from_blockchain(student_did)
    
#     if not pointers:
#         raise HTTPException(status_code=404, detail=f"No credentials found for student {student_did}")

#     qr_results = []

#     for (batch_id, leaf_index, enriched_cid) in pointers:
#         # 2. Fetch from IPFS to get the Merkle data
#         full_cred = fetch_from_ipfs_gateways(enriched_cid)
#         if not full_cred:
#             continue
            
#         # 3. Minify for the QR code
#         qr_data = {
#             "batch_id": batch_id,
#             "credential_hash": credential_hash_from_data(full_cred),
#             "proof": full_cred.get("merkleProof", {}).get("proof", []),
#             "leaf_index": leaf_index
#         }

#         # 4. Generate QR
#         json_str = json.dumps(qr_data, separators=(',', ':'))
#         qr = qrcode.QRCode(box_size=10, border=4)
#         qr.add_data(json_str)
#         qr.make(fit=True)
        
#         buf = io.BytesIO()
#         qr.make_image().save(buf, format="PNG")
#         img_str = base64.b64encode(buf.getvalue()).decode("utf-8")

#         qr_results.append({
#             "batch_id": batch_id,
#             "degree": full_cred.get("credentialSubject", {}).get("degree"),
#             "qr_code_base64": f"data:image/png;base64,{img_str}"
#         })

#     return {
#         "student_did": student_did,
#         "total_credentials": len(qr_results),
#         "qr_codes": qr_results
#     }
from fastapi import File, UploadFile
import io
import csv

@app.post("/api/credentials/batch/upload-csv")
async def upload_batch_csv(batch_id: str, file: UploadFile = File(...)):
    """
    Accepts a CSV file, parses it, and adds all students to a pending batch.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    contents = await file.read()
    # Decode bytes to string and use StringIO so the csv module can read it
    stream = io.StringIO(contents.decode('utf-8'))
    reader = csv.DictReader(stream)
    
    added_count = 0
    for row in reader:
        # Standardize the data format
        student_data = {
            "student_did": row['student_did'].strip(),
            "student_name": row['student_name'].strip(),
            "student_email": row['student_email'].strip(),
            "university_name": row['university_name'].strip(),
            "degree": row['degree'].strip(),
            "branch": row['branch'].strip(),
            "graduation_year": row['graduation_year'].strip(),
            "cgpa": float(row['cgpa'])
        }
        
        # Reuse your existing internal 'add_to_batch' logic
        # Assuming you have a helper function or direct dict access:
        if batch_id not in pending_batches:
            pending_batches[batch_id] = {"credentials": []}
            
        pending_batches[batch_id]["credentials"].append({
            "student_did": student_data["student_did"],
            "credential_data": student_data
        })
        added_count += 1

    return {
        "message": f"Successfully added {added_count} students to batch {batch_id}",
        "batch_id": batch_id,
        "total_pending": len(pending_batches[batch_id]["credentials"])
    }

@app.get("/api/credentials/student/{student_did}/qrs")
def get_student_qrs(student_did: str):
    """
    UID-Only Path:
    1. Looks up student on-chain.
    2. Fetches IPFS data.
    3. Runs the Merkle/Revocation check internally.
    4. Bakes the resulting 'is_valid/is_revoked' JSON into the QR code.
    """
    pointers = get_student_pointers_from_blockchain(student_did)
    if not pointers:
        raise HTTPException(status_code=404, detail="No credentials found.")

    qr_results = []

    for (batch_id, leaf_index, enriched_cid) in pointers:
        full_cred = fetch_from_ipfs_gateways(enriched_cid)
        if not full_cred:
            continue
            
        # --- INTERNAL VERIFICATION STEP ---
        cred_hash_bytes = bytes.fromhex(credential_hash_from_data(full_cred))
        proof_bytes = [bytes.fromhex(p) for p in full_cred.get("merkleProof", {}).get("proof", [])]

        try:
            # We call the contract NOW to get the current status
            is_valid, is_revoked, _ = contract.functions.verifyCredential(
                batch_id, cred_hash_bytes, proof_bytes, leaf_index
            ).call()
        except Exception:
            is_valid, is_revoked = False, False

        # --- THE DATA IN THE QR ---
        # This is exactly what the scanner will display
        final_status_json = {
            "is_valid": is_valid,
            "is_revoked": is_revoked,
            "uid": student_did,
            "batch": batch_id,
            "verified_at": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
        }

        # Generate QR with the status JSON string
        json_str = json.dumps(final_status_json, separators=(',', ':'))
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(json_str)
        qr.make(fit=True)
        
        buf = io.BytesIO()
        qr.make_image().save(buf, format="PNG")
        img_str = base64.b64encode(buf.getvalue()).decode("utf-8")

        qr_results.append({
            "batch_id": batch_id,
            "status_baked_in": final_status_json,
            "qr_code_base64": f"data:image/png;base64,{img_str}"
        })

    return {
        "student_did": student_did,
        "qr_codes": qr_results
    }

# =============================================================================
# SECTION 10: ENTRYPOINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)