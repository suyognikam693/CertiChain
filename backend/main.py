"""
CertiChain Backend — FastAPI + Neon PostgreSQL
Fake blockchain UX, real DB persistence.
"""

import hashlib
import json
import io
import csv
import random
import string
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
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
    allow_origins=["*"],
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
# IMPORTANT: "name" must match the name field in your CSV exactly
# so the student vault query can find their credential
# ──────────────────────────────────────────────
STUDENT_USERS = {
    "suyog":   {"password": "123", "name": "Suyog Nikam",   "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"},
    "aaditya": {"password": "456", "name": "Aaditya Sharma", "wallet": "0x8f3d12Cc5541C0532811a2b933Bc8d6484f1cDa"},
    "priya":   {"password": "789", "name": "Priya Singh",    "wallet": "0x1a2b33Cc7722D0641925c4b744Cc0f8695g2cFb"},
    "rahul":   {"password": "321", "name": "Rahul Verma",    "wallet": "0x9e4f56Dd8833E1752036d5c855Dd1g9706h3dGc"},
    "ananya":  {"password": "654", "name": "Ananya Iyer",    "wallet": "0x3c5d78Ee9944F2863147e6d966Ee2h0817i4eHd"},
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

BATCHES = {}



# ──────────────────────────────────────────────
# DB Init — runs every startup, safe to re-run
# ──────────────────────────────────────────────
def init_db():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS credentials (
            id              SERIAL PRIMARY KEY,
            did             TEXT NOT NULL DEFAULT 'UNKNOWN',
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

    # Safe migrations for anyone who created table before these columns existed
    migrations = [
        ("did",             "TEXT NOT NULL DEFAULT 'UNKNOWN'"),
        ("chain_id",        "INT DEFAULT 137"),
        ("block_number",    "BIGINT"),
        ("tx_hash",         "TEXT"),
        ("polygon_address", "TEXT"),
        ("revoked_at",      "TIMESTAMPTZ"),
    ]
    for col, definition in migrations:
        cur.execute(f"ALTER TABLE credentials ADD COLUMN IF NOT EXISTS {col} {definition};")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_credentials_hash ON credentials(hash);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_credentials_did  ON credentials(did);")

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
    """Deterministic SHA-256 of a sorted JSON payload."""
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return "0x" + hashlib.sha256(canonical.encode()).hexdigest()


def fake_receipt() -> dict:
    block = random.randint(43_000_000, 46_000_000)
    tx    = "0x" + "".join(random.choices(string.hexdigits.lower(), k=64))
    addr  = "0x4a2b" + "".join(random.choices(string.hexdigits.lower(), k=36)) + "c91e"
    return {"block_number": block, "tx_hash": tx, "chain_id": 137, "polygon_address": addr}


def create_token(username: str, role: str) -> str:
    payload = {
        "sub":  username,
        "role": role,
        "exp":  datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(tok: str) -> dict:
    try:
        return jwt.decode(tok, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired — please log in again")
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

class BatchAddRequest(BaseModel):
    batch_id: str
    student_did: str = ""
    student_name: str = ""
    student_email: str = ""
    university_name: str = ""
    degree: str = ""
    branch: str = ""
    graduation_year: str = ""
    cgpa: str = ""

class BatchCommitRequest(BaseModel):
    batch_id: str

class VerifyProofRequest(BaseModel):
    batch_id: str = ""
    credential_hash: str
    proof: list[str] = []
    leaf_index: int = 0


# ══════════════════════════════════════════════
# AUTH ENDPOINTS
# ══════════════════════════════════════════════

@app.post("/api/auth/student/login")
def student_login(body: StudentLoginRequest):
    user = STUDENT_USERS.get(body.username)
    if not user or user["password"] != body.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {
        "token":    create_token(body.username, "student"),
        "role":     "student",
        "name":     user["name"],
        "wallet":   user["wallet"],
        "username": body.username,
    }


@app.post("/api/auth/university/login")
def university_login(body: UniversityLoginRequest):
    user = UNIVERSITY_USERS.get(body.username)
    if not user or user["password"] != body.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {
        "token":    create_token(body.username, "university"),
        "role":     "university",
        "name":     user["name"],
        "username": body.username,
        "chain_id": user["chain_id"],
    }


# ══════════════════════════════════════════════
# UNIVERSITY — Upload CSV
# ══════════════════════════════════════════════

@app.post("/api/university/upload-csv")
def upload_csv(
    file: UploadFile = File(...),
    payload: dict = Depends(require_university),
    db = Depends(get_db),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files accepted")

    content = file.file.read().decode("utf-8-sig")  # handles BOM from Excel
    reader  = csv.DictReader(io.StringIO(content))
    rows    = list(reader)

    if not rows:
        raise HTTPException(status_code=400, detail="CSV is empty")

    university_name = UNIVERSITY_USERS[payload["sub"]]["name"]
    results = []
    cur = db.cursor()

    for row in rows:
        # Strip whitespace from all keys and values
        student = {k.strip(): v.strip() for k, v in row.items() if k}

        # ── 2-column format: "Student ID" + "Student Details (JSON)" ──
        if not student.get("legal_name") and "Student Details (JSON)" in student:
            try:
                details = json.loads(student["Student Details (JSON)"])
                student["legal_name"] = details.get("name", "Unknown")
                student["student_id"] = student.get("Student ID", "")
                student.update(details)  # merge all detail fields
            except Exception:
                pass

        # Skip rows with no name
        if not student.get("legal_name"):
            continue

        # Determine DID from whatever column is present
        did = (
            student.get("student_id")
            or student.get("Student ID")
            or student.get("did")
            or "UNKNOWN"
        )

        cert_hash = sha256_json(student)
        receipt   = fake_receipt()

        try:
            cur.execute(
                """
                INSERT INTO credentials
                    (did, hash, student_data, university, issued_by,
                     block_number, tx_hash, chain_id, polygon_address)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (hash) DO NOTHING
                RETURNING id
                """,
                (
                    did,
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
                "name":    student.get("legal_name"),
                "did":     did,
                "hash":    cert_hash,
                "status":  "issued" if inserted else "duplicate",
                "tx_hash": receipt["tx_hash"],
                "block":   receipt["block_number"],
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


# ══════════════════════════════════════════════
# UNIVERSITY — Dashboard / Revoke
# ══════════════════════════════════════════════

@app.get("/api/university/credentials")
def list_credentials(
    payload: dict = Depends(require_university),
    db = Depends(get_db),
):
    university_name = UNIVERSITY_USERS[payload["sub"]]["name"]
    cur = db.cursor()
    cur.execute(
        """
        SELECT id, did, hash, student_data, issued_at, is_revoked,
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
        "message":    "Credential revoked — new ledger state emitted",
        "hash":       body.hash,
        "revoked_at": datetime.utcnow().isoformat(),
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
            COUNT(*)                                                     AS total_issued,
            COUNT(*) FILTER (WHERE is_revoked = FALSE)                  AS active,
            COUNT(*) FILTER (WHERE is_revoked = TRUE)                   AS revoked,
            COUNT(*) FILTER (WHERE issued_at >= NOW() - INTERVAL '24 hours'
                             AND   is_revoked = FALSE)                  AS anchored_today
        FROM credentials
        WHERE university = %s
        """,
        (university_name,),
    )
    row = cur.fetchone()
    cur.close()
    return dict(row)


# ══════════════════════════════════════════════
# STUDENT — Vault
# ══════════════════════════════════════════════

@app.get("/api/student/credentials")
def student_credentials(
    payload: dict = Depends(require_student),
    db = Depends(get_db),
):
    username = payload["sub"]
    user     = STUDENT_USERS[username]
    name     = user["name"]
    cur      = db.cursor()

    # Match on legal_name OR name (covers both CSV formats) OR wallet
    cur.execute(
        """
        SELECT id, did, hash, student_data, university, issued_at,
               is_revoked, block_number, tx_hash, chain_id
        FROM credentials
        WHERE
            student_data->>'legal_name'    ILIKE %s
            OR student_data->>'name'       ILIKE %s
            OR student_data->>'wallet_address' = %s
        ORDER BY issued_at DESC
        """,
        (f"%{name}%", f"%{name}%", user["wallet"]),
    )
    rows = cur.fetchall()
    cur.close()

    return {
        "name":        user["name"],
        "wallet":      user["wallet"],
        "credentials": [dict(r) for r in rows],
    }


# ══════════════════════════════════════════════
# STUDENT CREDENTIALS BY DID
# ══════════════════════════════════════════════

@app.get("/api/credentials/student/{student_did}")
def get_student_credentials_by_did(student_did: str, db = Depends(get_db)):
    cur = db.cursor()
    cur.execute("SELECT hash, is_revoked, id, student_data FROM credentials WHERE did = %s", (student_did,))
    rows = cur.fetchall()
    cur.close()
    
    results = []
    for r in rows:
        mock_proof = "0x" + hashlib.sha256(str(r["id"]).encode()).hexdigest()
        sd = r["student_data"]
        
        results.append({
            "credential_hash": r["hash"],
            "proof": [mock_proof],
            "ipfs_cid": f"QmMockCIDFor{r['hash'][:8]}",
            "cid": f"QmMockCIDFor{r['hash'][:8]}",
            "degree": sd.get("degree_class", sd.get("degree", "Degree")),
            "program": sd.get("program", sd.get("major", "Program")),
            "university": sd.get("university", "University"),
            "student_name": sd.get("student_name", sd.get("legal_name", sd.get("name", "Student"))),
            "issued_at": r.get("issued_at", ""),
            "isVerified": not r["is_revoked"]
        })
    return {"credentials": results}

@app.get("/api/credentials/student/{student_did}/qrs")
def get_student_qrs(student_did: str, db = Depends(get_db)):
    cur = db.cursor()
    cur.execute("SELECT hash, is_revoked, student_data FROM credentials WHERE did = %s", (student_did,))
    rows = cur.fetchall()
    cur.close()
    
    qrs = []
    for r in rows:
        status = "REVOKED" if r["is_revoked"] else "VERIFIED"
        data = {
            "hash": r["hash"],
            "did": student_did,
            "status": status,
            "degree": r["student_data"].get("degree_class", r["student_data"].get("degree", "Degree"))
        }
        qrs.append({
            "qr_data": json.dumps(data)
        })
    return qrs

# ══════════════════════════════════════════════
# EMPLOYER — Public Verify (no auth needed)
# ══════════════════════════════════════════════

@app.post("/api/credentials/verify-with-proof")
def verify_credential_with_proof(body: VerifyProofRequest, db = Depends(get_db)):
    cur = db.cursor()
    cur.execute("SELECT * FROM credentials WHERE hash = %s", (body.credential_hash,))
    row = cur.fetchone()
    cur.close()
    
    if not row:
        return {
            "is_valid": False, 
            "is_revoked": False, 
            "message": "No credential matching this hash exists in the registry."
        }
    
    sd = row["student_data"]
    
    return {
        "is_valid": True,
        "is_revoked": row["is_revoked"],
        "university_name": row["university"],
        "graduation_year": sd.get("graduation_year", sd.get("year", "N/A")),
        "student_name": sd.get("student_name", sd.get("legal_name", sd.get("name", "N/A"))),
        "degree": sd.get("degree_class", sd.get("degree", "N/A")),
        "metadata": sd,
        "chain_id": row["chain_id"],
        "tx_hash": row["tx_hash"],
        "block_number": row["block_number"]
    }

@app.get("/api/credentials/{batch_id}/{leaf_index}/share-link")
def get_share_link(batch_id: str, leaf_index: int):
    # Simulated share link to employer portal
    url = f"http://localhost:5173/employer?batch_id={batch_id}&leaf_index={leaf_index}"
    return {"url": url}

@app.post("/api/verify")
def verify_credential(body: VerifyHashRequest, db = Depends(get_db)):
    h = body.hash.strip()
    if not h:
        raise HTTPException(status_code=400, detail="Hash is required")

    cur = db.cursor()
    cur.execute(
        """
        SELECT hash, did, student_data, university, issued_at,
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
        # Clean not-found response — no exception, just found: false
        return {
            "found":   False,
            "status":  "NOT_FOUND",
            "message": "No credential matching this hash exists in the registry.",
        }

    row          = dict(row)
    sd           = row["student_data"]
    student_name = sd.get("legal_name") or sd.get("name") or "—"
    program      = sd.get("program")    or sd.get("major") or "—"
    degree_class = sd.get("degree_class") or sd.get("degree") or "—"

    return {
        "found":           True,
        "status":          "REVOKED" if row["is_revoked"] else "VERIFIED",
        "hash":            row["hash"],
        "did":             row["did"],
        "student_name":    student_name,
        "program":         program,
        "degree_class":    degree_class,
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
    return verify_credential(VerifyHashRequest(hash=cert_hash), db)


# ══════════════════════════════════════════════
# BATCH ISSUANCE ENDPOINTS
# ══════════════════════════════════════════════

@app.post("/api/credentials/batch/add")
def batch_add_json(body: BatchAddRequest, payload: dict = Depends(require_university)):
    if body.batch_id not in BATCHES:
        BATCHES[body.batch_id] = []
    
    cred_data = body.dict()
    student = {
        "legal_name": body.student_name,
        "did": body.student_did,
        "email": body.student_email,
        "degree_class": body.degree,
        "program": body.branch,
        "cgpa": body.cgpa,
        "graduation_year": body.graduation_year
    }
    cred_data["raw_student"] = student
    
    BATCHES[body.batch_id].append(cred_data)
    leaf_index = len(BATCHES[body.batch_id]) - 1
    
    # Generate mock IPFS for this addition
    bare_cid = "Qm" + "".join(random.choices(string.ascii_letters + string.digits, k=44))
    
    return {
        "status": "success",
        "leaf_index": leaf_index,
        "ipfs_cid": bare_cid
    }

@app.post("/api/credentials/batch/upload-csv")
def batch_upload_csv(
    batch_id: str,
    file: UploadFile = File(...),
    payload: dict = Depends(require_university)
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files accepted")
    
    content = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    
    if batch_id not in BATCHES:
        BATCHES[batch_id] = []
        
    added = 0
    for row in rows:
        student = {k.strip(): v.strip() for k, v in row.items() if k}
        
        if not student.get("legal_name") and "Student Details (JSON)" in student:
            try:
                details = json.loads(student["Student Details (JSON)"])
                student["legal_name"] = details.get("name", "Unknown")
                student["student_id"] = student.get("Student ID", "")
                student.update(details)
            except Exception:
                pass
        
        if not student.get("legal_name"):
            continue
            
        did = student.get("student_id") or student.get("Student ID") or student.get("did") or "UNKNOWN"
        cred_data = {
            "batch_id": batch_id,
            "student_did": did,
            "student_name": student.get("legal_name"),
            "raw_student": student
        }
        BATCHES[batch_id].append(cred_data)
        added += 1
        
    return {"status": "success", "added": added}

@app.post("/api/credentials/batch/commit")
def batch_commit(body: BatchCommitRequest, payload: dict = Depends(require_university), db = Depends(get_db)):
    if body.batch_id not in BATCHES or len(BATCHES[body.batch_id]) == 0:
        raise HTTPException(status_code=400, detail="Batch empty or not found")
        
    items = BATCHES[body.batch_id]
    university_name = UNIVERSITY_USERS[payload["sub"]]["name"]
    cur = db.cursor()
    
    merkle_base = "".join([sha256_json(i["raw_student"]) for i in items])
    merkle_root = "0x" + hashlib.sha256(merkle_base.encode()).hexdigest()
    
    receipt = fake_receipt()
    
    for item in items:
        student = item["raw_student"]
        cert_hash = sha256_json(student)
        did = item["student_did"]
        
        try:
            cur.execute(
                """
                INSERT INTO credentials
                    (did, hash, student_data, university, issued_by,
                     block_number, tx_hash, chain_id, polygon_address)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (hash) DO NOTHING
                """,
                (
                    did, cert_hash, json.dumps(student), university_name,
                    payload["sub"], receipt["block_number"], receipt["tx_hash"],
                    receipt["chain_id"], receipt["polygon_address"]
                ),
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
            
    db.commit()
    cur.close()
    
    del BATCHES[body.batch_id]
    
    return {
        "status": "success",
        "merkle_root": merkle_root,
        "tx_hash": receipt["tx_hash"]
    }

# ══════════════════════════════════════════════
# HEALTH
# ══════════════════════════════════════════════

@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}