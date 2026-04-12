#!/usr/bin/env python3
"""
test_flow.py — end-to-end smoke test for the proof-in-IPFS credential system.

Tests the full lifecycle:
  add -> add -> commit -> student lookup (proof from IPFS) -> verify-with-proof -> revoke

Run:
  python test_flow.py

Requires the FastAPI server to be running at http://localhost:8000.
"""

import json
import sys
import requests

BASE    = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}
AUTH    = {"Authorization": "Bearer dev-key"}

BATCH_ID = "TEST-BATCH-010"

STUDENTS = [
    {
        "batch_id":        BATCH_ID,
        "student_did":     "2023800017",
        "student_name":    "Nitin Verma",
        "student_email":   "nitin@spit.ac.in",
        "university_name": "SPIT",
        "degree":          "B.Tech",
        "branch":          "CSE",
        "graduation_year": "2027",
        "cgpa":            9.1,
    },
    {
        "batch_id":        BATCH_ID,
        "student_did":     "2023800018",
        "student_name":    "Piysh Chawla",
        "student_email":   "Piyus@spit.ac.in",
        "university_name": "SPIT",
        "degree":          "B.Tech",
        "branch":          "CSE",
        "graduation_year": "2027",
        "cgpa":            8.5,
    },
    {
        "batch_id":        BATCH_ID,
        "student_did":     "2023800019",
        "student_name":    "Samay Khan",
        "student_email":   "Samay@spit.ac.in",
        "university_name": "SPIT",
        "degree":          "B.Tech",
        "branch":          "CSE",
        "graduation_year": "2027",
        "cgpa":            9.7,
    },
]


def ok(label: str, resp: requests.Response) -> dict:
    if resp.status_code not in (200, 201):
        print(f"FAIL [{label}]: HTTP {resp.status_code}")
        print(resp.text[:500])
        sys.exit(1)
    data = resp.json()
    print(f"OK   [{label}]")
    return data


def main():
    print("=" * 60)
    print("Credential Verifier — end-to-end smoke test")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 0. Health check
    # ------------------------------------------------------------------
    r = requests.get(f"{BASE}/health")
    ok("health", r)
    health = r.json()
    print(f"     status      : {health['status']}")
    print(f"     blockchain  : {health['components']['blockchain']['connected']}")
    print(f"     ipfs cluster: {health['components']['ipfs_cluster']['reachable']}")

    # ------------------------------------------------------------------
    # 1. Add students to batch
    # ------------------------------------------------------------------
    print()
    print("--- Step 1: Add credentials to batch ---")
    for s in STUDENTS:
        r   = requests.post(f"{BASE}/api/credentials/batch/add", json=s, headers=HEADERS)
        d   = ok(f"add {s['student_did']}", r)
        print(f"     leaf_index   : {d['leaf_index']}")
        print(f"     bare_cid     : {d.get('bare_ipfs_cid')}")

    # ------------------------------------------------------------------
    # 2. Commit batch
    # ------------------------------------------------------------------
    print()
    print("--- Step 2: Commit batch ---")
    r = requests.post(f"{BASE}/api/credentials/batch/commit", json={"batch_id": BATCH_ID}, headers=HEADERS)
    commit = ok("commit", r)
    print(f"     merkle_root  : {commit['merkle_root'][:24]}...")
    print(f"     tx_hash      : {commit.get('tx_hash')}")
    print(f"     enriched_cids:")
    for cid in commit.get("enriched_cids", []):
        print(f"       {cid}")

    # ------------------------------------------------------------------
    # 3. Student lookup — proof must come back from IPFS
    # ------------------------------------------------------------------
    print()
    print("--- Step 3: Student credential lookup (proof from IPFS) ---")

    # Test all three students; keep first one for verify step
    verify_targets = []
    for s in STUDENTS:
        r    = requests.get(f"{BASE}/api/credentials/student/{s['student_did']}")
        data = ok(f"student {s['student_did']}", r)

        creds = data.get("credentials", [])
        if not creds:
            print(f"FAIL: no credentials returned for {s['student_did']}")
            sys.exit(1)

        cred = creds[0]

        # Validate that proof is populated from IPFS
        proof = cred.get("proof", [])
        if not proof:
            print(f"FAIL: proof is empty for {s['student_did']} — IPFS fetch may have failed")
            sys.exit(1)

        if not cred.get("credential_hash"):
            print(f"FAIL: credential_hash missing for {s['student_did']}")
            sys.exit(1)

        if not cred.get("merkle_root"):
            print(f"FAIL: merkle_root missing for {s['student_did']}")
            sys.exit(1)

        print(f"     {s['student_did']} ({cred['student_name']})")
        print(f"       batch_id        : {cred['batch_id']}")
        print(f"       leaf_index      : {cred['leaf_index']}")
        print(f"       credential_hash : {cred['credential_hash'][:24]}...")
        print(f"       proof siblings  : {len(proof)}")
        print(f"       merkle_root     : {cred['merkle_root'][:24]}...")
        print(f"       ipfs_cid        : {cred['ipfs_cid']}")

        verify_targets.append(cred)

    # ------------------------------------------------------------------
    # 4. Verify each credential with Merkle proof
    # ------------------------------------------------------------------
    print()
    print("--- Step 4: verify-with-proof (on-chain) ---")
    for cred in verify_targets:
        payload = {
            "batch_id":        cred["batch_id"],
            "credential_hash": cred["credential_hash"],
            "proof":           cred["proof"],
            "leaf_index":      cred["leaf_index"],
        }
        r    = requests.post(f"{BASE}/api/credentials/verify-with-proof", json=payload, headers=HEADERS)
        data = ok(f"verify leaf {cred['leaf_index']}", r)
        print(f"     is_valid   : {data['is_valid']}")
        print(f"     is_revoked : {data['is_revoked']}")
        print(f"     message    : {data['message']}")
        if not data["is_valid"]:
            print("FAIL: credential should be valid at this point")
            sys.exit(1)

    # ------------------------------------------------------------------
    # 5. Revoke first credential and re-verify
    # ------------------------------------------------------------------
    print()
    print("--- Step 5: Revoke first credential ---")
    first = verify_targets[0]
    r = requests.post(
        f"{BASE}/api/credentials/revoke",
        json={"batch_id": first["batch_id"], "credential_hash": first["credential_hash"]},
        headers={**HEADERS, **AUTH},
    )
    ok("revoke", r)
    print(f"     revoked: {first['credential_hash'][:24]}...")

    # Re-verify — should now come back revoked
    payload = {
        "batch_id":        first["batch_id"],
        "credential_hash": first["credential_hash"],
        "proof":           first["proof"],
        "leaf_index":      first["leaf_index"],
    }
    r    = requests.post(f"{BASE}/api/credentials/verify-with-proof", json=payload, headers=HEADERS)
    data = ok("verify after revoke", r)
    print(f"     is_valid   : {data['is_valid']}")
    print(f"     is_revoked : {data['is_revoked']}")
    if not data["is_revoked"]:
        print("FAIL: credential should be revoked")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 6. Confirm non-revoked credentials are still valid
    # ------------------------------------------------------------------
    print()
    print("--- Step 6: Other credentials still valid ---")
    for cred in verify_targets[1:]:
        payload = {
            "batch_id":        cred["batch_id"],
            "credential_hash": cred["credential_hash"],
            "proof":           cred["proof"],
            "leaf_index":      cred["leaf_index"],
        }
        r    = requests.post(f"{BASE}/api/credentials/verify-with-proof", json=payload, headers=HEADERS)
        data = ok(f"verify leaf {cred['leaf_index']} still valid", r)
        if not data["is_valid"] or data["is_revoked"]:
            print("FAIL: non-revoked credential should still be valid")
            sys.exit(1)
        print(f"     leaf {cred['leaf_index']}: is_valid={data['is_valid']} is_revoked={data['is_revoked']}")

    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
