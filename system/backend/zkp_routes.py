# =============================================================================
# zkp_routes.py  — paste these into main.py (or import and include the router)
# =============================================================================
# Add these 3 things to main.py:
#
#   1. Two new Pydantic models (at the bottom of SECTION 4)
#   2. generate_cgpa_proof() endpoint
#   3. verify_cgpa_threshold() endpoint
#
# Also add to SECTION 3 (blockchain setup):
#   CGPA_VERIFIER_ADDRESS = os.getenv("CGPA_VERIFIER_ADDRESS")
# =============================================================================

import subprocess
import json
import os
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Optional, List

# ---------------------------------------------------------------------------
# ADD TO SECTION 4: Pydantic Models
# ---------------------------------------------------------------------------

class GenerateCGPAProofRequest(BaseModel):
    # student_did is used to look up the credential and get the actual CGPA
    student_did:     str
    batch_id:        str
    leaf_index:      int
    # threshold is set by the employer — e.g. 9.0 → send 900
    threshold_cgpa:  float   = 9.0    # employer's minimum, e.g. 9.0

class VerifyCGPAThresholdRequest(BaseModel):
    batch_id:        str
    credential_hash: str
    merkle_proof:    List[str]
    leaf_index:      int
    threshold:       int               # e.g. 900 (= 9.00 * 100)
    pA:              List[str]         # ZK proof component A
    pB:              List[List[str]]   # ZK proof component B (2x2)
    pC:              List[str]         # ZK proof component C


# ---------------------------------------------------------------------------
# ADD TO SECTION 7: API Routes
# ---------------------------------------------------------------------------

# Path to zkp_helper.js — adjust if your folder structure differs
ZKP_HELPER_PATH = os.path.join(os.path.dirname(__file__), "zkp_helper.js")


@app.post("/api/credentials/zkp/generate-proof")
def generate_cgpa_proof(request: GenerateCGPAProofRequest):
    """
    Student calls this to generate a ZK proof that their CGPA >= threshold.
    The actual CGPA is fetched from IPFS (the enriched credential), used
    to generate the proof, then DISCARDED — never returned to the caller.

    Returns: pA, pB, pC (the ZK proof) + threshold (public signal).
    The student sends these to the employer or to /zkp/verify-threshold.
    """
    # --- 1. Fetch the student's enriched credential from IPFS ---------------
    pointers = get_student_pointers_from_blockchain(request.student_did)
    target   = None
    for (batch_id, leaf_index, enriched_cid) in pointers:
        if batch_id == request.batch_id and leaf_index == request.leaf_index:
            target = (batch_id, leaf_index, enriched_cid)
            break

    if not target:
        raise HTTPException(
            status_code=404,
            detail=f"No credential found for batch '{request.batch_id}' leaf {request.leaf_index}"
        )

    _, _, enriched_cid = target
    full_cred = fetch_from_ipfs_gateways(enriched_cid)
    if not full_cred:
        raise HTTPException(status_code=502, detail="Could not fetch credential from IPFS.")

    # --- 2. Extract CGPA from credential subject ----------------------------
    cgpa_float = full_cred.get("credentialSubject", {}).get("cgpa")
    if cgpa_float is None:
        raise HTTPException(status_code=400, detail="Credential does not contain a CGPA field.")

    # Convert to integer (multiply by 100 to remove decimal)
    # 9.25 → 925,  10.0 → 1000,  8.5 → 850
    cgpa_int      = int(round(float(cgpa_float) * 100))
    threshold_int = int(round(request.threshold_cgpa * 100))

    # --- 3. Call zkp_helper.js via subprocess --------------------------------
    # The actual CGPA (cgpa_int) is the PRIVATE input — never logged or returned
    try:
        result = subprocess.run(
            ["node", ZKP_HELPER_PATH, str(cgpa_int), str(threshold_int)],
            capture_output=True,
            text=True,
            timeout=60,    # proof generation can take ~5-10 seconds
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Proof generation timed out.")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="node not found. Is Node.js installed?")

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"zkp_helper.js error: {result.stderr}")

    try:
        proof_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Could not parse proof output: {result.stdout[:200]}")

    if not proof_data.get("success"):
        # Student's CGPA is below threshold — proof cannot be generated
        return {
            "success":   False,
            "meets_threshold": False,
            "threshold": request.threshold_cgpa,
            "message":   proof_data.get("error", "CGPA does not meet threshold."),
        }

    # --- 4. Return proof (CGPA itself is NOT included in the response) -------
    return {
        "success":         True,
        "meets_threshold": True,
        "threshold":       request.threshold_cgpa,
        "threshold_int":   threshold_int,
        # These three are the ZK proof — send to employer or /zkp/verify-threshold
        "pA":              proof_data["pA"],
        "pB":              proof_data["pB"],
        "pC":              proof_data["pC"],
        "pubSignals":      proof_data["pubSignals"],
        "message":         f"Proof generated. CGPA meets threshold of {request.threshold_cgpa}. Actual CGPA not revealed.",
    }


@app.post("/api/credentials/zkp/verify-threshold")
def verify_cgpa_threshold(request: VerifyCGPAThresholdRequest):
    """
    Employer calls this to verify on-chain:
      1. The credential is authentic (Merkle proof check)
      2. The student's CGPA >= threshold (ZK proof check)
      3. The credential is not revoked

    The employer never learns the actual CGPA — only that it meets the bar.
    """
    if not contract:
        raise HTTPException(status_code=503, detail="Blockchain unavailable.")

    try:
        credential_hash_bytes = bytes.fromhex(request.credential_hash)
        merkle_proof_bytes    = [bytes.fromhex(p) for p in request.merkle_proof]

        # Convert pA, pB, pC from hex strings to integers for the contract call
        pA = [int(request.pA[0], 16), int(request.pA[1], 16)]
        pB = [
            [int(request.pB[0][0], 16), int(request.pB[0][1], 16)],
            [int(request.pB[1][0], 16), int(request.pB[1][1], 16)],
        ]
        pC = [int(request.pC[0], 16), int(request.pC[1], 16)]

        # Call the combined on-chain verifier
        cred_valid, cgpa_valid, is_revoked = contract.functions.verifyCGPAThreshold(
            request.batch_id,
            credential_hash_bytes,
            merkle_proof_bytes,
            request.leaf_index,
            request.threshold,
            pA,
            pB,
            pC,
        ).call()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"On-chain verification failed: {e}")

    return {
        "credential_valid": cred_valid,
        "cgpa_valid":       cgpa_valid,
        "is_revoked":       is_revoked,
        "threshold":        request.threshold / 100,   # convert back: 900 → 9.0
        "fully_verified":   cred_valid and cgpa_valid and not is_revoked,
        "message": (
            "Credential is authentic and CGPA meets threshold."
            if (cred_valid and cgpa_valid and not is_revoked)
            else "Verification failed. Check credential_valid, cgpa_valid, is_revoked fields."
        ),
    }
