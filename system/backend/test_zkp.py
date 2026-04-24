#!/usr/bin/env python3
"""
test_zkp.py — end-to-end ZKP smoke test.

Tests the full ZKP flow on top of an already-committed batch:
  generate proof (CGPA meets threshold) → verify on-chain → confirm pass
  generate proof (CGPA below threshold) → confirm graceful fail

Run AFTER test_flow.py has already committed a batch.
Or run standalone — it commits its own batch first.

Usage:
  python test_zkp.py
"""

import json
import sys
import requests

BASE     = "http://localhost:8000"
HEADERS  = {"Content-Type": "application/json"}
BATCH_ID = "ZKP-TEST-BATCH-001"

# Student with high CGPA (should pass threshold of 9.0)
HIGH_CGPA_STUDENT = {
    "batch_id":        BATCH_ID,
    "student_did":     "zkp-student-001",
    "student_name":    "Priya Sharma",
    "student_email":   "priya@spit.ac.in",
    "university_name": "SPIT",
    "degree":          "B.Tech",
    "branch":          "CSE",
    "graduation_year": "2027",
    "cgpa":            9.5,   # above 9.0 threshold → should PASS
}

# Student with low CGPA (should fail threshold of 9.0)
LOW_CGPA_STUDENT = {
    "batch_id":        BATCH_ID,
    "student_did":     "zkp-student-002",
    "student_name":    "Arjun Mehta",
    "student_email":   "arjun@spit.ac.in",
    "university_name": "SPIT",
    "degree":          "B.Tech",
    "branch":          "CSE",
    "graduation_year": "2027",
    "cgpa":            8.2,   # below 9.0 threshold → should FAIL
}


def ok(label, resp):
    if resp.status_code not in (200, 201):
        print(f"FAIL [{label}]: HTTP {resp.status_code} — {resp.text[:300]}")
        sys.exit(1)
    data = resp.json()
    print(f"OK   [{label}]")
    return data


def main():
    print("=" * 60)
    print(" ZKP Smoke Test — CGPA Threshold Verification")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Setup: commit a fresh batch with two students
    # ------------------------------------------------------------------
    print("\n--- Setup: committing test batch ---")

    for s in [HIGH_CGPA_STUDENT, LOW_CGPA_STUDENT]:
        r = requests.post(f"{BASE}/api/credentials/batch/add", json=s, headers=HEADERS)
        d = ok(f"add {s['student_did']} (cgpa={s['cgpa']})", r)
        print(f"     leaf_index: {d['leaf_index']}")

    r      = requests.post(f"{BASE}/api/credentials/batch/commit", json={"batch_id": BATCH_ID}, headers=HEADERS)
    commit = ok("commit batch", r)
    print(f"     merkle_root : {commit['merkle_root'][:24]}...")
    print(f"     tx_hash     : {commit.get('tx_hash')}")

    # ------------------------------------------------------------------
    # 2. Fetch student credentials (to get proof + credential_hash)
    # ------------------------------------------------------------------
    print("\n--- Fetching student credentials from IPFS ---")

    r_high = requests.get(f"{BASE}/api/credentials/student/zkp-student-001")
    high   = ok("fetch high CGPA student", r_high)
    high_cred = high["credentials"][0]
    print(f"     credential_hash : {high_cred['credential_hash'][:24]}...")
    print(f"     proof siblings  : {len(high_cred['proof'])}")

    r_low = requests.get(f"{BASE}/api/credentials/student/zkp-student-002")
    low   = ok("fetch low CGPA student", r_low)
    low_cred = low["credentials"][0]

    # ------------------------------------------------------------------
    # 3. Generate ZK proof — high CGPA student (should succeed)
    # ------------------------------------------------------------------
    print("\n--- Generating ZK proof (CGPA 9.5 >= threshold 9.0) ---")
    r = requests.post(f"{BASE}/api/credentials/zkp/generate-proof", json={
        "student_did":    "zkp-student-001",
        "batch_id":       BATCH_ID,
        "leaf_index":     0,
        "threshold_cgpa": 9.0,
    }, headers=HEADERS)
    proof_data = ok("generate proof (high CGPA)", r)
    print(f"     meets_threshold : {proof_data['meets_threshold']}")
    print(f"     pA[0]           : {proof_data['pA'][0][:20]}...")
    assert proof_data["meets_threshold"] is True, "High CGPA student should meet threshold"

    # ------------------------------------------------------------------
    # 4. Verify on-chain — should pass
    # ------------------------------------------------------------------
    print("\n--- On-chain ZK verification (should PASS) ---")
    r = requests.post(f"{BASE}/api/credentials/zkp/verify-threshold", json={
        "batch_id":        BATCH_ID,
        "credential_hash": high_cred["credential_hash"],
        "merkle_proof":    high_cred["proof"],
        "leaf_index":      high_cred["leaf_index"],
        "threshold":       900,   # 9.00 * 100
        "pA":              proof_data["pA"],
        "pB":              proof_data["pB"],
        "pC":              proof_data["pC"],
    }, headers=HEADERS)
    verify = ok("verify on-chain (high CGPA)", r)
    print(f"     credential_valid : {verify['credential_valid']}")
    print(f"     cgpa_valid       : {verify['cgpa_valid']}")
    print(f"     fully_verified   : {verify['fully_verified']}")
    print(f"     message          : {verify['message']}")
    assert verify["fully_verified"] is True, "Verification should pass for high CGPA student"

    # ------------------------------------------------------------------
    # 5. Generate ZK proof — low CGPA student (should gracefully fail)
    # ------------------------------------------------------------------
    print("\n--- Generating ZK proof (CGPA 8.2 < threshold 9.0) — expect fail ---")
    r = requests.post(f"{BASE}/api/credentials/zkp/generate-proof", json={
        "student_did":    "zkp-student-002",
        "batch_id":       BATCH_ID,
        "leaf_index":     1,
        "threshold_cgpa": 9.0,
    }, headers=HEADERS)
    d = ok("generate proof (low CGPA)", r)
    print(f"     meets_threshold : {d['meets_threshold']}")
    print(f"     message         : {d['message']}")
    assert d["meets_threshold"] is False, "Low CGPA student should NOT meet threshold"

    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print(" ALL ZKP TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
