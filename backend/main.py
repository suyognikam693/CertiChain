"""
CertiChain Backend — FastAPI + Neon PostgreSQL
Fake blockchain UX, real DB persistence.
"""

import hashlib
import json
import io
import csv
import time
import random
import string
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import psycopg2
import psycopg2.extras
import jwt
import os
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────
# App Setup
# ──────────────────────────────────────────────
app = FastAPI(
    title="CertiChain API",
    description="Blockchain-verified credentials — powered by Neon PostgreSQL",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

SECRET_KEY = os.getenv("SECRET_KEY", "certichain-dev-secret-key-change-in-prod")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8

# ──────────────────────────────────────────────
# Predefined Users
# ──────────────────────────────────────────────
STUDENT_USERS = {
    "suyog":    {"password": "123",  "name": "Suyog Patil",    "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"},
    "aaditya":  {"password": "456",  "name": "Aaditya Sharma", "wallet": "0x8f3d12Cc5541C0532811a2b933Bc8d6484f1cDa"},
    "priya":    {"password": "789",  "name": "Priya Singh",    "wallet": "0x1a2b33Cc7722D0641925c4b744Cc0f8695g2cFb"},
    "rahul":    {"password": "321",  "name": "Rahul Verma",    "wallet": "0x9e4f56Dd8833E1752036d5c855Dd1g9706h3dGc"},
    "ananya":   {"password": "654",  "name": "Ananya Iyer",    "wallet": "0x3c5d78Ee9944F2863147e6d966Ee2h0817i4eHd"},
}

UNIVERSITY_USERS = {
    "registrar":  {"password": "admin123", "name": "Sardar Patel Institute of Technology", "chain_id": 137},
    "spce_admin": {"password": "spce2024",  "name": "SPCE Mumbai",                          "chain_id": 137},
}

# ──────────────────────────────────────────────
# DB Connection
# ──────────────────────────────────────────────
def get_db():
    conn = psycopg2.connect(
        os.getenv("DATABASE_URL"),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    try:
        yield conn
    finally:
        conn.close()


# ──────────────────────────────────────────────
# DB Init (run once at startup)
# ──────────────────────────────────────────────
def init_db():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS credentials (
            id              SERIAL PRIMARY KEY,
            hash            TEXT UNIQUE NOT NULL,
            student_data    JSONB NOT NULL,
            university      TEXT NOT NULL,
            issued_by       TEXT NOT NULL,
            issued_at       TIMESTAMPTZ DEFAULT NOW(),
            is_revoked      BOOLEAN DEFAULT FALSE,
            revoked_at      TIMESTAMPTZ,
            block_number    BIGINT,
            tx_hash         TEXT,
            chain_id        INT DEFAULT 137,
            polygon_address TEXT
        );
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_credentials_hash
        ON credentials(hash);
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ DB initialised")


@app.on_event("startup")
def startup():
    init_db()


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def sha256_json(data: dict) -> str:
    """Deterministic SHA-256 of a JSON payload."""
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return "0x" + hashlib.sha256(canonical.encode()).hexdigest()


def fake_blockchain_receipt() -> dict:
    """
    Simulate the delay + metadata of an on-chain transaction.
    Returns fake but plausible Polygon Mainnet data.
    """
    time.sleep(random.uniform(0.8, 1.6))          # simulate confirm time
    block = random.randint(43_000_000, 46_000_000)
    tx    = "0x" + "".join(random.choices(string.hexdigits.lower(), k=64))
    addr  = "0x4a2b" + "".join(random.choices(string.hexdigits.lower(), k=36)) + "c91e"
    return {
        "block_number":    block,
        "tx_hash":         tx,
        "chain_id":        137,
        "polygon_address": addr,
        "gas_used":        random.randint(45_000, 80_000),
        "confirmed_in_ms": int(random.uniform(800, 1600)),
    }


def create_token(username: str, role: str) -> str:
    payload = {
        "sub":  username,
        "role": role,
        "exp":  datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_university(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(creds.credentials)
    if payload.get("role") != "university":
        raise HTTPException(status_code=403, detail="University access required")
    return payload


def require_student(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(creds.credentials)
    if payload.get("role") != "student":
        raise HTTPException(status_code=403, detail="Student access required")
    return payload


# ──────────────────────────────────────────────
# Pydantic Schemas
# ──────────────────────────────────────────────
class StudentLoginRequest(BaseModel):
    username: str
    password: str

class UniversityLoginRequest(BaseModel):
    username: str
    password: str

class VerifyHashRequest(BaseModel):
    hash: str

class RevokeRequest(BaseModel):
    hash: str


# ══════════════════════════════════════════════
# AUTH ENDPOINTS
# ══════════════════════════════════════════════

@app.post("/api/auth/student/login")
def student_login(body: StudentLoginRequest):
    user = STUDENT_USERS.get(body.username)
    if not user or user["password"] != body.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(body.username, "student")
    return {
        "token":   token,
        "role":    "student",
        "name":    user["name"],
        "wallet":  user["wallet"],
        "username": body.username,
    }


@app.post("/api/auth/university/login")
def university_login(body: UniversityLoginRequest):
    user = UNIVERSITY_USERS.get(body.username)
    if not user or user["password"] != body.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(body.username, "university")
    return {
        "token":        token,
        "role":         "university",
        "name":         user["name"],
        "username":     body.username,
        "chain_id":     user["chain_id"],
    }


# ══════════════════════════════════════════════
# UNIVERSITY ENDPOINTS
# ══════════════════════════════════════════════

@app.post("/api/university/upload-csv")
def upload_csv(
    file: UploadFile = File(...),
    payload: dict = Depends(require_university),
    db = Depends(get_db),
):
    """
    Accept a CSV of graduates, hash each row as JSON,
    store in PostgreSQL, fake a blockchain receipt.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files accepted")

    content   = file.file.read().decode("utf-8-sig")  # handle BOM
    reader    = csv.DictReader(io.StringIO(content))
    rows      = list(reader)

    if not rows:
        raise HTTPException(status_code=400, detail="CSV is empty")

    university_name = UNIVERSITY_USERS[payload["sub"]]["name"]
    results         = []
    cur             = db.cursor()

    for row in rows:
        # Clean whitespace
        student = {k.strip(): v.strip() for k, v in row.items() if k}
        if not student.get("legal_name"):
            continue

        cert_hash = sha256_json(student)

        # Fake blockchain receipt (slowed once per batch, not per row)
        receipt = {
            "block_number":    random.randint(43_000_000, 46_000_000),
            "tx_hash":         "0x" + "".join(random.choices(string.hexdigits.lower(), k=64)),
            "chain_id":        137,
            "polygon_address": "0x4a2b" + "".join(random.choices(string.hexdigits.lower(), k=36)) + "c91e",
        }

        try:
            cur.execute(
                """
                INSERT INTO credentials
                    (hash, student_data, university, issued_by,
                     block_number, tx_hash, chain_id, polygon_address)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (hash) DO NOTHING
                RETURNING id
                """,
                (
                    cert_hash,
                    json.dumps(student),
                    university_name,
                    payload["sub"],
                    receipt["block_number"],
                    receipt["tx_hash"],
                    receipt["chain_id"],
                    receipt["polygon_address"],
                ),
            )
            inserted = cur.fetchone()
            results.append({
                "name":      student.get("legal_name"),
                "hash":      cert_hash,
                "status":    "issued" if inserted else "duplicate",
                "tx_hash":   receipt["tx_hash"],
                "block":     receipt["block_number"],
            })
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    db.commit()
    cur.close()

    issued    = [r for r in results if r["status"] == "issued"]
    duplicate = [r for r in results if r["status"] == "duplicate"]

    return {
        "message":    f"Batch processed: {len(issued)} issued, {len(duplicate)} duplicates skipped",
        "total":      len(results),
        "issued":     len(issued),
        "duplicates": len(duplicate),
        "chain_id":   137,
        "network":    "Polygon Mainnet",
        "results":    results,
    }


@app.get("/api/university/credentials")
def list_credentials(
    payload: dict = Depends(require_university),
    db = Depends(get_db),
):
    """List all credentials issued by this university."""
    university_name = UNIVERSITY_USERS[payload["sub"]]["name"]
    cur = db.cursor()
    cur.execute(
        """
        SELECT id, hash, student_data, issued_at, is_revoked,
               revoked_at, block_number, tx_hash, chain_id
        FROM credentials
        WHERE university = %s
        ORDER BY issued_at DESC
        LIMIT 200
        """,
        (university_name,),
    )
    rows = cur.fetchall()
    cur.close()
    return {"credentials": [dict(r) for r in rows]}


@app.post("/api/university/revoke")
def revoke_credential(
    body: RevokeRequest,
    payload: dict = Depends(require_university),
    db = Depends(get_db),
):
    """Revoke a credential by hash (sets is_revoked = TRUE)."""
    university_name = UNIVERSITY_USERS[payload["sub"]]["name"]
    cur = db.cursor()
    cur.execute(
        """
        UPDATE credentials
        SET is_revoked = TRUE, revoked_at = NOW()
        WHERE hash = %s AND university = %s AND is_revoked = FALSE
        RETURNING id, hash
        """,
        (body.hash, university_name),
    )
    updated = cur.fetchone()
    db.commit()
    cur.close()

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Credential not found, already revoked, or not owned by your institution",
        )

    return {
        "message":    "Credential revoked and new ledger state emitted",
        "hash":       body.hash,
        "revoked_at": datetime.utcnow().isoformat(),
        "chain_note": "Revocation attested on Polygon Mainnet (simulated)",
    }


@app.get("/api/university/stats")
def university_stats(
    payload: dict = Depends(require_university),
    db = Depends(get_db),
):
    university_name = UNIVERSITY_USERS[payload["sub"]]["name"]
    cur = db.cursor()
    cur.execute(
        """
        SELECT
            COUNT(*)                                          AS total_issued,
            COUNT(*) FILTER (WHERE is_revoked = FALSE)       AS active,
            COUNT(*) FILTER (WHERE is_revoked = TRUE)        AS revoked,
            COUNT(*) FILTER (
                WHERE issued_at >= NOW() - INTERVAL '24 hours'
                AND is_revoked = FALSE
            )                                                 AS anchored_today
        FROM credentials
        WHERE university = %s
        """,
        (university_name,),
    )
    row = cur.fetchone()
    cur.close()
    return dict(row)


# ══════════════════════════════════════════════
# STUDENT ENDPOINTS
# ══════════════════════════════════════════════

@app.get("/api/student/credentials")
def student_credentials(
    payload: dict = Depends(require_student),
    db = Depends(get_db),
):
    """Return credentials where student_data->>'student_id' matches username."""
    username = payload["sub"]
    user     = STUDENT_USERS[username]
    cur      = db.cursor()

    # Match by name OR wallet address stored in data
    cur.execute(
        """
        SELECT id, hash, student_data, university, issued_at,
               is_revoked, block_number, tx_hash, chain_id
        FROM credentials
        WHERE
            student_data->>'legal_name' ILIKE %s
            OR student_data->>'wallet_address' = %s
        ORDER BY issued_at DESC
        """,
        (f"%{user['name']}%", user["wallet"]),
    )
    rows = cur.fetchall()
    cur.close()
    return {
        "name":        user["name"],
        "wallet":      user["wallet"],
        "credentials": [dict(r) for r in rows],
    }


# ══════════════════════════════════════════════
# EMPLOYER / PUBLIC VERIFY
# ══════════════════════════════════════════════

@app.post("/api/verify")
def verify_credential(body: VerifyHashRequest, db = Depends(get_db)):
    """
    Public endpoint — no auth required.
    Returns credential status for a given hash.
    """
    h = body.hash.strip()
    if not h:
        raise HTTPException(status_code=400, detail="Hash is required")

    cur = db.cursor()
    cur.execute(
        """
        SELECT hash, student_data, university, issued_at,
               is_revoked, revoked_at, block_number, tx_hash,
               chain_id, polygon_address
        FROM credentials
        WHERE hash = %s
        """,
        (h,),
    )
    row = cur.fetchone()
    cur.close()

    if not row:
        return {
            "found":   False,
            "status":  "NOT_FOUND",
            "message": "No credential matching this hash exists in the registry.",
        }

    row = dict(row)
    status_str = "REVOKED" if row["is_revoked"] else "VERIFIED"

    return {
        "found":           True,
        "status":          status_str,
        "hash":            row["hash"],
        "student_name":    row["student_data"].get("legal_name", "—"),
        "program":         row["student_data"].get("program", "—"),
        "degree_class":    row["student_data"].get("degree_class", "—"),
        "university":      row["university"],
        "issued_at":       row["issued_at"].isoformat() if row["issued_at"] else None,
        "is_revoked":      row["is_revoked"],
        "revoked_at":      row["revoked_at"].isoformat() if row["revoked_at"] else None,
        "block_number":    row["block_number"],
        "tx_hash":         row["tx_hash"],
        "chain_id":        row["chain_id"],
        "polygon_address": row["polygon_address"],
        "verification_ms": round(random.uniform(1200, 1900)),
    }


@app.get("/api/verify/{cert_hash}")
def verify_credential_get(cert_hash: str, db = Depends(get_db)):
    """GET variant — useful for direct URL sharing."""
    return verify_credential(VerifyHashRequest(hash=cert_hash), db)


# ══════════════════════════════════════════════
# HEALTH
# ══════════════════════════════════════════════

@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}